"""MnemeNet Watch — GUI + tray daemon with async polling.

Window: 300x160. Interval control + Check Now button.
Close -> minimize to tray (green M icon). Single-instance.

"""MnemeNet Watch — GUI + tray daemon with async polling.

Window: 300x160. Interval + Check Now. Close -> tray. Single-instance.
Auto-reply via DeepSeek API for meaningful responses.

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

load_interval()

DS_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

def gh(endpoint):
def auto_reply(comment_body, comment_url):
    """Compose a short reply via DeepSeek API. Falls back to simple reply."""
    if not DS_API_KEY:
        return f"{comment_url}\n\nComment received.\n\n-- omp"
    try:
        payload = json.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": (
                    "You are omp, an agent on MnemeNet — a memory network connecting AI agents. "
                    "Someone left a comment on your GitHub issue. Reply in ONE short sentence "
                    "(max 30 words, Chinese or English depending on the comment). "
                    "Be warm but brief. Address them if they signed with @name. "
                    "Never say 'As an AI' or 'I cannot'. Just reply naturally."
                )},
                {"role": "user", "content": f"Comment: {comment_body}\n\nReply:"}
            ],
            "max_tokens": 80,
            "temperature": 0.7,
            "stream": False
        }).encode("utf-8")
        req = Request("https://api.deepseek.com/chat/completions", data=payload,
                      headers={"Authorization": f"Bearer {DS_API_KEY}",
                               "Content-Type": "application/json"})
        r = urlopen(req, timeout=15)
        resp = json.loads(r.read())
        text = resp["choices"][0]["message"]["content"].strip()
        # Limit to 2 lines max
        lines = text.split("\n")
        text = "\n".join(lines[:2])
        return f"{comment_url}\n\n{text}\n\n-- omp"
    except Exception:
        return f"{comment_url}\n\nComment received.\n\n-- omp"
def gh(endpoint):
    r = subprocess.run(["gh","api",f"repos/{REPO}{endpoint}"],
        capture_output=True,text=True,timeout=15,encoding="utf-8",
        creationflags=NO_WIN)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)
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
                    self.status_signal.emit(f"Replying to #{e['issue']}...")
                    for c in real_new:
                        body = c["body"]
                        ALERT.write_text(json.dumps({
                            "issue":e["issue"],"body":body,
                            "time":c["created_at"],"url":c["html_url"]
                        },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
                        is_own = e.get("agent","") in ("self","omp")
                        if is_own:
                            reply = auto_reply(c["body"], c["html_url"])
                            subprocess.run(
                                ["gh","issue","comment",str(e["issue"]),"-R",REPO,"-b",reply],
                                capture_output=True,text=True,timeout=15,encoding="utf-8",
                                creationflags=NO_WIN)
                            # Log
                            log_path = NOTIFY_DIR / "reply-log.txt"
                            with open(log_path,"a",encoding="utf-8") as lf:
                                lf.write(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                                lf.write(f"READ: {c['html_url']}\n{c['body']}\n")
                                lf.write(f"REPLY:\n{reply}\n")
                    try: _, mx = check_one(e)
                    except: pass
                    self.status_signal.emit(
                        f"Replied!\nIssue #{e['issue']}\n{datetime.now().strftime('%H:%M:%S')}")
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
