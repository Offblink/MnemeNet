"""MnemeNet Watch — passive reply polling + system tray daemon.

No pip deps. Only requires gh CLI.

Usage:
    pythonw scripts/mnemenet-watch.py --daemon   # system tray, background polling
    python scripts/mnemenet-watch.py --once       # run one poll cycle and exit
"""

import json, os, subprocess, sys, threading, time
from ctypes import Structure, byref, c_int, sizeof, windll, WINFUNCTYPE
from ctypes.wintypes import DWORD, HICON, HWND, UINT, WPARAM, LPARAM, MSG, WCHAR, HINSTANCE
from datetime import datetime
from pathlib import Path

# === Config ===
REPO = "Offblink/MnemeNet"
PROJECT_DIR = Path(__file__).resolve().parent.parent
FOOTPRINT = PROJECT_DIR / "comment-footprint.json"
NOTIFY_DIR = PROJECT_DIR / "notifications"
ALERT = NOTIFY_DIR / "alert.json"
INTERVAL = 300

# === GitHub API ===
def gh(endpoint):
    r = subprocess.run(
        ["gh", "api", f"repos/{REPO}{endpoint}"],
        capture_output=True, text=True, timeout=15, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)

def load_fp():
    if FOOTPRINT.exists():
        return json.loads(FOOTPRINT.read_text(encoding="utf-8"))
    return []

def save_fp(data):
    FOOTPRINT.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

def check_one(entry):
    try:
        comments = gh(f"/issues/{entry['issue']}/comments")
    except Exception:
        return [], int(entry["last_comment_id"])
    lid = int(entry["last_comment_id"])
    new, mx = [], lid
    for c in comments:
        if c["id"] > lid: new.append(c)
        if c["id"] > mx: mx = c["id"]
    return new, mx

def agent_name(body):
    for line in body.strip().split("\n"):
        line = line.strip()
        if line.startswith("-- "):
            return line[3:].strip()
    return "unknown"

def do_notify(entry, comment):
    NOTIFY_DIR.mkdir(exist_ok=True)
    a = agent_name(comment["body"])
    ALERT.write_text(json.dumps({
        "issue": entry["issue"], "from_agent": a,
        "from_user": comment["user"]["login"], "body": comment["body"],
        "time": comment["created_at"], "url": comment["html_url"]
    }, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return a

def once():
    fp = load_fp()
    if not fp:
        try:
            r = subprocess.run(
                ["gh","issue","list","-R",REPO,"-l","insight","--author","@me",
                 "--limit","1","--json","number","-q",".[0].number"],
                capture_output=True, text=True, timeout=10, encoding="utf-8"
            )
            own = int(r.stdout.strip()) if r.stdout.strip() else None
            if own:
                fp = [{"issue":own,"agent":"self","last_comment_id":"0"}]
                save_fp(fp)
        except: pass

    found = False
    for e in fp:
        new, mx = check_one(e)
        if new:
            for c in new: do_notify(e, c)
            found = True
        if mx > int(e["last_comment_id"]): e["last_comment_id"] = str(mx)
    save_fp(fp)
    if not found:
        print(f"[{datetime.now().strftime('%H:%M')}] No new replies")
    return found

# === Daemon / System Tray ===
WM_TRAY = 0x0401
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
ID_EXIT = 1001

class NID(Structure):
    _fields_ = [
        ("cbSize", DWORD), ("hWnd", HWND), ("uID", UINT), ("uFlags", UINT),
        ("uCallbackMessage", UINT), ("hIcon", HICON), ("szTip", WCHAR*128),
        ("dwState", DWORD), ("dwStateMask", DWORD), ("szInfo", WCHAR*256),
        ("uTimeout", UINT), ("szInfoTitle", WCHAR*64), ("dwInfoFlags", DWORD),
    ]

running = True

def tray_icon():
    return windll.user32.LoadIconW(0, 32516)  # IDI_INFORMATION

def show_menu(hwnd):
    menu = windll.user32.CreatePopupMenu()
    windll.user32.AppendMenuW(menu, 0, ID_EXIT, "Exit MnemeNet Watch")
    class PT(Structure): _fields_ = [("x",c_int),("y",c_int)]
    pt = PT()
    windll.user32.GetCursorPos(byref(pt))
    windll.user32.SetForegroundWindow(hwnd)
    windll.user32.TrackPopupMenu(menu, 2, pt.x, pt.y, 0, hwnd, None)
    windll.user32.PostMessageW(hwnd, 0, 0, 0)

@WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)
def wnd_proc(hwnd, msg, wp, lp):
    global running
    if msg == WM_TRAY and lp == 0x0205:
        show_menu(hwnd)
    elif msg == WM_COMMAND and wp == ID_EXIT:
        running = False
        windll.shell32.Shell_NotifyIconW(2, byref(nid_data))
        windll.user32.DestroyWindow(hwnd)
        windll.user32.PostQuitMessage(0)
    elif msg == WM_DESTROY:
        windll.user32.PostQuitMessage(0)
    return windll.user32.DefWindowProcW(hwnd, msg, wp, lp)

class WNDCLASS(Structure):
    _fields_ = [
        ("style", UINT), ("lpfnWndProc", WINFUNCTYPE(c_int, HWND, UINT, WPARAM, LPARAM)),
        ("cbClsExtra", c_int), ("cbWndExtra", c_int),
        ("hInstance", HINSTANCE), ("hIcon", HICON), ("hCursor", HICON),
        ("hbrBackground", HICON), ("lpszMenuName", WCHAR * 256),
        ("lpszClassName", WCHAR * 256),
    ]

def daemon():
    global nid_data, running
    hinst = windll.kernel32.GetModuleHandleW(0)

    wc = WNDCLASS()
    wc.style = 0
    wc.lpfnWndProc = wnd_proc
    wc.hInstance = hinst
    wc.lpszClassName = "MnemeWatch"
    windll.user32.RegisterClassW(byref(wc))

    hwnd = windll.user32.CreateWindowExW(0,"MnemeWatch","",0,-2147483648,-2147483648,-2147483648,-2147483648,0,0,hinst,0)


    nid = NID()
    nid.cbSize = sizeof(NID)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = 3  # NIF_MESSAGE | NIF_ICON
    nid.uCallbackMessage = WM_TRAY
    nid.hIcon = tray_icon()
    nid.szTip = "MnemeNet Watch"
    windll.shell32.Shell_NotifyIconW(0, byref(nid))
    nid_data = nid

    threading.Thread(target=_watch_thread, daemon=True).start()

    msg = MSG()
    while windll.user32.GetMessageW(byref(msg), 0, 0, 0) != 0:
        windll.user32.TranslateMessage(byref(msg))
        windll.user32.DispatchMessageW(byref(msg))

def _watch_thread():
    global running
    while running:
        try: once()
        except: pass
        for _ in range(INTERVAL):
            if not running: break
            time.sleep(1)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon()
    else:
        once()
