"""MnemeNet Watch Tray — minimal system tray wrapper.

Usage: pythonw scripts/mnemenet-tray.pyw
Background thread runs mnemenet-watch --once every 5 min.
Green dot icon. Right-click → Exit.

Requires PyQt6: pip install PyQt6
"""

import subprocess, sys, threading, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WATCH_PY = SCRIPT_DIR / "mnemenet-watch.pyw"
INTERVAL = 300

try:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
    from PyQt6.QtCore import Qt
except ImportError:
    print("PyQt6 not installed. Run: pip install PyQt6")
    sys.exit(1)

WATCH_PY = SCRIPT_DIR / "mnemenet-watch.pyw"
INTERVAL = 300
def watch_loop():
    while running:
        try:
            subprocess.run(
                [sys.executable, str(WATCH_PY), "--once"],
                capture_output=True, text=True, timeout=30, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(INTERVAL):
            if not running: break
            time.sleep(1)

def make_icon():
    pix = QPixmap(16, 16)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(0, 180, 80))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 12, 12)
    p.end()
    return QIcon(pix)

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

tray = QSystemTrayIcon()
tray.setIcon(make_icon())
tray.setToolTip("MnemeNet Watch")

menu = QMenu()
menu.addAction("Exit").triggered.connect(lambda: (set_running(False), app.quit()))
tray.setContextMenu(menu)
tray.show()

def set_running(v):
    global running; running = v

threading.Thread(target=watch_loop, daemon=True).start()
app.exec()
