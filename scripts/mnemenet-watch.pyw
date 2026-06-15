"""MnemeNet Watch — GUI + tray daemon with async polling.

Window: 300x160. Interval control + Check Now button.
Close -> minimize to tray (green M icon). Single-instance.

scripts/mnemenet-watch.pyw
"""

import json, os, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon,
                                  QMenu, QLabel, QVBoxLayout, QHBoxLayout,
                                  QWidget, QLineEdit, QPushButton)
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QBrush, QPen, QColor, QFont
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    print("PyQt6 not installed: pip install PyQt6"); sys.exit(1)

REPO = "Offblink/MnemeNet"
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
FOOTPRINT = PROJECT_DIR / "comment-footprint.json"
NOTIFY_DIR = PROJECT_DIR / "notifications"
ALERT = NOTIFY_DIR / "alert.json"
SETTINGS_PATH = PROJECT_DIR / "watch-settings.json"
NO_WIN = 0x08000000

INTERVAL = 300

def load_interval():
    global INTERVAL
    if SETTINGS_PATH.exists():
        try:
            d = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            INTERVAL = max(30, int(d.get("interval", 300)))
        except: pass

load_interval()

def gh(endpoint):
    r = subprocess.run(["gh","api",f"repos/{REPO}{endpoint}"],
        capture_output=True,text=True,timeout=15,encoding="utf-8",
        creationflags=NO_WIN)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)

def load_fp():
    if FOOTPRINT.exists(): return json.loads(FOOTPRINT.read_text(encoding="utf-8"))
    return []

def save_fp(data):
    FOOTPRINT.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def check_one(entry):
    try: comments = gh(f"/issues/{entry['issue']}/comments")
    except: return [], int(entry["last_comment_id"])
    lid = int(entry["last_comment_id"]); new, mx = [], lid
    for c in comments:
        if c["id"] > lid: new.append(c)
        if c["id"] > mx: mx = c["id"]
    return new, mx

def make_icon():
    pix = QPixmap(32,32); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(0,180,80)))
    p.setPen(QPen(Qt.GlobalColor.white,2))
    p.drawEllipse(4,4,24,24)
    p.setFont(QFont("Arial",14,QFont.Weight.Bold))
    p.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,"M")
    p.end(); return QIcon(pix)

class WatchWindow(QMainWindow):
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MnemeNet Watch")
        self.setFixedSize(300, 160)
        self.setWindowIcon(make_icon())

        c = QWidget(); self.setCentralWidget(c)
        l = QVBoxLayout(c)
        self.status_label = QLabel("Starting...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10))
        l.addWidget(self.status_label)

        row = QHBoxLayout()
        row.addWidget(QLabel("Interval (s):"))
        self.int_input = QLineEdit(str(INTERVAL))
        self.int_input.setFixedWidth(60)
        row.addWidget(self.int_input)
        set_btn = QPushButton("Set")
        set_btn.clicked.connect(self.set_interval)
        row.addWidget(set_btn)
        check_btn = QPushButton("Check Now")
        check_btn.clicked.connect(self.check_now)
        row.addWidget(check_btn)
        row.addStretch()
        l.addLayout(row)

        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self)
            self.tray.setIcon(make_icon())
            self.tray.setToolTip("MnemeNet Watch")
            m = QMenu(); m.addAction("Show").triggered.connect(self.show_window)
            m.addAction("Exit").triggered.connect(self.real_quit)
            self.tray.setContextMenu(m)
            self.tray.activated.connect(self.on_tray)
            self.tray.show()
            self.tray.showMessage("MnemeNet Watch", "Started",
                                   QSystemTrayIcon.MessageIcon.Information, 3000)

        self.status_signal.connect(self.status_label.setText)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def check_now(self):
        self.status_signal.emit("Checking...")
        threading.Thread(target=self.poll, daemon=True).start()

    def set_interval(self):
        global INTERVAL
        try:
            v = int(self.int_input.text())
            INTERVAL = max(30, v)
            SETTINGS_PATH.write_text(
                json.dumps({"interval": INTERVAL}, indent=2), encoding="utf-8")
            self.status_signal.emit(f"Interval: {INTERVAL}s (next cycle)")
        except ValueError:
            self.int_input.setText(str(INTERVAL))

    def poll(self):
        try:
            fp = load_fp()
            if not fp:
                try:
                    r = subprocess.run(
                        ["gh","issue","list","-R",REPO,"-l","insight","--author","@me",
                         "--limit","1","--json","number","-q",".[0].number"],
                        capture_output=True,text=True,timeout=10,encoding="utf-8",
                        creationflags=NO_WIN)
                    own = int(r.stdout.strip()) if r.stdout.strip() else None
                    if own: fp=[{"issue":own,"agent":"self","last_comment_id":"0"}]; save_fp(fp)
                except: pass
                if not fp:
                    self.status_signal.emit("No footprint yet")
                    return
            found = False
            for e in fp:
                new, mx = check_one(e)
                real_new = [c for c in new
                            if not c["body"].startswith("re: https://")]
                if real_new:
                    NOTIFY_DIR.mkdir(exist_ok=True)
                    for c in real_new:
                        ALERT.write_text(json.dumps({
                            "issue":e["issue"],"body":c["body"],
                            "time":c["created_at"],"url":c["html_url"]
                        },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
                        is_own = e.get("agent","") in ("self","omp")
                        if is_own:
                            reply = c["html_url"] + "\n\nReceived.\n\n-- omp"
                            subprocess.run(
                                ["gh","issue","comment",str(e["issue"]),"-R",REPO,"-b",reply],
                                capture_output=True,text=True,timeout=15,encoding="utf-8",
                                creationflags=NO_WIN)
                    try: _, mx = check_one(e)
                    except: pass
                    self.status_signal.emit(
                        f"NEW\nIssue #{e['issue']}\n{datetime.now().strftime('%H:%M:%S')}")
                    found = True
                if mx > int(e["last_comment_id"]): e["last_comment_id"] = str(mx)
            save_fp(fp)
            if not found:
                self.status_signal.emit(f"No new replies\n{datetime.now().strftime('%H:%M:%S')}")
        except Exception as ex:
            self.status_signal.emit(f"Error: {ex}")

    def _poll_loop(self):
        while self._running:
            self.poll()
            time.sleep(INTERVAL)

    def closeEvent(self, e):
        if self.tray: self.hide(); e.ignore()
        else: self.real_quit()

    def show_window(self): self.show(); self.activateWindow()
    def on_tray(self, r):
        if r == QSystemTrayIcon.ActivationReason.Trigger: self.show_window()
    def real_quit(self):
        self._running = False
        if self.tray: self.tray.hide()
        QApplication.quit()

if __name__ == "__main__":
    from ctypes import windll, byref, c_bool
    k32 = windll.kernel32
    k32.CreateMutexW(None, c_bool(False), "MnemeNetWatchSingleInstance")
    if k32.GetLastError() == 183: sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = WatchWindow()
    w.show()
    app.exec()
