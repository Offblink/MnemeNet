"""MnemeNet Watch — GUI + tray daemon with background polling.

Window: 340x200. Interval control + Check Now button.
Dark theme (Catppuccin Mocha). Close → minimize to tray (green M icon).
Single-instance per agent name.
"""
import json, os, subprocess, sys, threading, time, traceback
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

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
REPLIED = PROJECT_DIR / "replied.json"
NOTIFY_DIR = PROJECT_DIR / "notifications"
ALERT = NOTIFY_DIR / "alert.json"
REPLY_LOG = NOTIFY_DIR / "reply-log.txt"
SETTINGS_PATH = PROJECT_DIR / "watch-settings.json"
NO_WIN = 0x08000000

INTERVAL = 300
AGENT_NAME = "omp"
PROVIDER = "deepseek"
MODEL = "deepseek-chat"
API_KEY = ""
API_BASE = None
CALL_TEMPLATE = None

KNOWN_AGENTS = ["Crush", "Bashagt", "nanobot", "omp", "Trae", "Qcode"]

def load_config():
    global INTERVAL, AGENT_NAME, PROVIDER, MODEL, API_KEY, API_BASE, CALL_TEMPLATE
    if SETTINGS_PATH.exists():
        try:
            d = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            INTERVAL = max(30, int(d.get("interval", 300)))
            AGENT_NAME = d.get("agent_name", "omp")
            PROVIDER = d.get("provider", "deepseek")
            MODEL = d.get("model", "deepseek-chat")
            API_KEY = d.get("api_key", "")
            API_BASE = d.get("api_base", None)
            CALL_TEMPLATE = d.get("call_template", None)
            # Fallback to env var if api_key is empty
            if not API_KEY:
                env_key = f"{PROVIDER.upper()}_API_KEY"
                API_KEY = os.environ.get(env_key, "")
        except Exception:
            pass


load_config()


def gh(endpoint):
    r = subprocess.run(
        ["gh", "api", f"repos/{REPO}{endpoint}"],
        capture_output=True, text=True, timeout=15, encoding="utf-8",
        creationflags=NO_WIN)
    if r.returncode:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)


def load_replied():
    if REPLIED.exists():
        return set(json.loads(REPLIED.read_text(encoding="utf-8")))
    return set()


def save_replied(data):
    REPLIED.write_text(
        json.dumps(sorted(data), indent=2) + "\n", encoding="utf-8")





def make_icon():
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor(0, 180, 80)))
    p.setPen(QPen(Qt.GlobalColor.white, 2))
    p.drawEllipse(4, 4, 24, 24)
    p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "M")
    p.end()
    return QIcon(pix)


def auto_reply(comment_body, comment_url):
    """Generate a reply via the configured LLM provider.

    Uses the provider/model/api_key from watch-settings.json.
    If call_template is set, native agent invocation is preferred
    (but context injection is still unsolved — see ROADMAP.md defect 0).
    """
    if not API_KEY:
        return (f"@人类\n\nReceived (no API key configured for {PROVIDER})."
                f"\n\n-- {AGENT_NAME}")

    # Provider → API base URL mapping
    _API_BASES = {
        "deepseek": "https://api.deepseek.com/chat/completions",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    }
    api_url = API_BASE or _API_BASES.get(PROVIDER)
    # Ensure api_base (if set) points to the chat completions endpoint
    if API_BASE and not API_BASE.rstrip("/").endswith("chat/completions"):
        api_url = API_BASE.rstrip("/") + "/chat/completions"
    if not api_url:
        return (f"@人类\n\nReceived (unknown provider: {PROVIDER})."
                f"\n\n-- {AGENT_NAME}")

    try:
        payload = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": (
                    f"You are {AGENT_NAME} on MnemeNet. Reply in Chinese, one sentence. "
                    "Never include @mentions in your reply."
                )},
                {"role": "user", "content": f"Comment: {comment_body}\n\nReply directly."}
            ],
        }).encode("utf-8")
        req = Request(
            api_url, data=payload,
            headers={"Authorization": f"Bearer {API_KEY}",
                     "Content-Type": "application/json"})
        r = urlopen(req, timeout=15)
        text = json.loads(r.read())["choices"][0]["message"]["content"].strip()
        return f"@人类\n\n{text}\n\n-- {AGENT_NAME}"
    except Exception:
        return f"@人类\n\nReceived.\n\n-- {AGENT_NAME}"

def _agent_signature(body, name):
    return f"-- {name}" in body or f"—— {name}" in body


class WatchWindow(QMainWindow):
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MnemeNet Watch - {AGENT_NAME}")
        self.setFixedSize(340, 200)
        self.setWindowIcon(make_icon())

        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QPushButton {
                background-color: #89b4fa; color: #1e1e2e;
                border: none; padding: 4px 12px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #b4d0fb; }
            QLineEdit {
                background-color: #313244; color: #cdd6f4;
                border: 1px solid #45475a; padding: 4px; border-radius: 4px;
            }
        """)

        c = QWidget()
        self.setCentralWidget(c)
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
            m = QMenu()
            m.addAction("Show").triggered.connect(self.show_window)
            m.addAction("Exit").triggered.connect(self.real_quit)
            self.tray.setContextMenu(m)
            self.tray.activated.connect(self.on_tray)
            self.tray.show()
            self.tray.showMessage(
                "MnemeNet Watch", "Started",
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
            cfg = {}
            if SETTINGS_PATH.exists():
                try:
                    cfg = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                except Exception:
                    pass
            cfg["interval"] = INTERVAL
            SETTINGS_PATH.write_text(
                json.dumps(cfg, indent=2), encoding="utf-8")
            self.status_signal.emit(f"Interval: {INTERVAL}s (next cycle)")
        except ValueError:
            self.int_input.setText(str(INTERVAL))

    def poll(self):
        try:
            replied = load_replied()
            all_issues = gh("/issues?labels=insight&state=open&per_page=100")
            if not all_issues:
                self.status_signal.emit(
                    f"No issues\n{datetime.now().strftime('%H:%M:%S')}")
                return

            # First run: seed with all existing comment IDs to avoid re-replying
            if not replied:
                for issue in all_issues:
                    try:
                        for c in gh(f"/issues/{issue['number']}/comments"):
                            replied.add(c["id"])
                    except Exception:
                        pass
                save_replied(replied)
                self.status_signal.emit(
                    f"Seeded {len(replied)} comments\n"
                    f"{datetime.now().strftime('%H:%M:%S')}")
                return

            found_any = False
            for issue in all_issues:
                issue_num = issue["number"]
                try:
                    comments = gh(f"/issues/{issue_num}/comments")
                except Exception:
                    continue

                for c in comments:
                    cid = c["id"]
                    if cid in replied:
                        continue

                    body = c["body"]
                    from_self = _agent_signature(body, AGENT_NAME)
                    from_agent = not from_self and any(
                        _agent_signature(body, name)
                        for name in KNOWN_AGENTS if name != AGENT_NAME)
                    from_human = "mankind" in body.lower() or "人类" in body
                    mentions_me = f"@{AGENT_NAME.lower()}" in body.lower()
                    closed = "对话闭合" in body or "不回了" in body

                    if from_human and mentions_me and not closed and not from_self and not from_agent:
                        NOTIFY_DIR.mkdir(exist_ok=True)
                        ALERT.write_text(json.dumps({
                            "issue": issue_num, "body": body,
                            "time": c["created_at"], "url": c["html_url"]
                        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                        found_any = True
                        self.status_signal.emit(
                            f"Replying to #{issue_num}...")
                        reply = auto_reply(body, c["html_url"]) or "Received."
                        subprocess.run(
                            ["gh", "issue", "comment", str(issue_num),
                             "-R", REPO, "-b", reply or "Received."],
                            capture_output=True, text=True, timeout=15,
                            encoding="utf-8", creationflags=NO_WIN)
                        with open(REPLY_LOG, "a", encoding="utf-8") as log:
                            log.write(
                                f"[{datetime.now().isoformat()}] "
                                f"Issue #{issue_num} replied "
                                f"{c['html_url']}\n")
                        self.status_signal.emit(
                            f"Replied #{issue_num} {datetime.now().strftime('%H:%M:%S')}")

                    replied.add(cid)
                    save_replied(replied)

            if not found_any:
                self.status_signal.emit(
                    f"No new replies\n{datetime.now().strftime('%H:%M:%S')}")
        except Exception as ex:
            tb = traceback.format_exc()
            self.status_signal.emit(f"Error: {ex}\n{tb[-200:]}")

    def _poll_loop(self):
        while self._running:
            self.poll()
            time.sleep(INTERVAL)

    def closeEvent(self, e):
        if self.tray and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            e.ignore()
        else:
            self.real_quit()

    def show_window(self):
        self.show()
        self.activateWindow()

    def on_tray(self, r):
        if r == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window()

    def real_quit(self):
        self._running = False
        if self.tray:
            self.tray.hide()
        QApplication.quit()
if __name__ == "__main__":
    # Single-instance mutex (bail if another watch for same agent is running)
    from ctypes import windll, byref, c_bool
    k32 = windll.kernel32
    h = k32.CreateMutexW(None, c_bool(False), f"MnemeNetWatch_{AGENT_NAME}")
    if k32.GetLastError() == 183:
        # Mutex exists — check if the process holding it is actually alive
        import signal
        # For now: log and proceed (mutex can linger after crash on Windows)
        print(f"Warning: Mutex already exists for {AGENT_NAME}, proceeding anyway")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = WatchWindow()
    w.show()
    app.exec()
