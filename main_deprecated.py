import os
import re
import time
import subprocess
import xml.etree.ElementTree as ET

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
DEVICE     = "-s emulator-5554"
DIRECTORY  = r"C:\Users\yufanw\Downloads"
NOVO_APP   = "com.novo.insurance.client"
MOCK_APP   = "com.telenav.mocklocation"
ANSI = {
    "HEAD": "\033[95m", "B": "\033[94m", "G": "\033[92m",
    "R":    "\033[91m", "Y": "\033[33m", "END": "\033[0m",
}

# ─── LOW-LEVEL COMMANDS ─────────────────────────────────────────────────────────
def execute(cmd, silent=False):
    print(" >", ANSI["G"] + cmd + ANSI["END"])
    try:
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            cwd=DIRECTORY, capture_output=True,
            text=True, check=True
        )
        if not silent and result.stdout.strip():
            for line in result.stdout.splitlines():
                print(" | ", line)
        elif silent:
            print(" | ... output trimmed ...")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(ANSI["R"] + "Error:\n" +
              "\n".join(" | " + l for l in e.stderr.splitlines()) +
              ANSI["END"])
        return ""

def tap(x, y, delay=0.5):
    execute(f"adb {DEVICE} shell input tap {x} {y}")
    time.sleep(delay)

def sleep(t):
    print(ANSI["Y"] + f" | waiting {t}s" + ANSI["END"])
    time.sleep(t)

def warn(msg):
    print(ANSI["Y"] + " | " + msg + ANSI["END"])

def err(msg):
    print(ANSI["R"] + " ! " + msg + ANSI["END"])

# ─── XML / UI SCRAPING ──────────────────────────────────────────────────────────
def parse_bounds(s):
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", s))
    return x1, y1, x2, y2

def dump_ui():
    execute(f"adb {DEVICE} shell uiautomator dump")
    xml = execute(f"adb {DEVICE} shell cat /sdcard/window_dump.xml", silent=True)
    return ET.fromstring(xml)

def find_checkboxes(root):
    boxes = []
    for n in root.iter("node"):
        if n.attrib.get("class") != "android.widget.CheckBox":
            continue
        bounds = n.attrib.get("bounds", "")
        if not bounds:
            continue
        x1, y1, x2, y2 = parse_bounds(bounds)
        boxes.append({
            "center": ((x1+x2)//2, (y1+y2)//2),
            "y": (y1+y2)//2,
            "checked": n.attrib.get("checked") == "true"
        })
    return sorted(boxes, key=lambda b: b["y"])

def find_clickables(root):
    elems = []
    for n in root.iter("node"):
        if n.attrib.get("clickable") != "true":
            continue
        bounds = n.attrib.get("bounds", "")
        text   = n.attrib.get("text", "").strip()
        if not bounds:
            continue
        x1, y1, x2, y2 = parse_bounds(bounds)
        elems.append({
            "text": text,
            "center": ((x1+x2)//2, (y1+y2)//2),
            "y": (y1+y2)//2
        })
    return elems

# ─── DEVICE / APP HELPERS ───────────────────────────────────────────────────────
def get_screen_size():
    out = execute(f"adb {DEVICE} shell wm size")
    m = re.search(r"(\d+)x(\d+)", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    err("Could not read screen size; defaulting.")
    return 1080, 2400

def launch(app_id):
    execute(f"adb {DEVICE} shell monkey -p {app_id} 1")

def ensure_app_focus(app_id):
    win = execute(f"adb {DEVICE} shell dumpsys window", silent=True)
    m = re.search(r"mCurrentFocus=.*\s([^/]+)/", win)
    if not m or m.group(1) != app_id:
        # toggle app switch to reset focus
        execute(f"adb {DEVICE} shell input keyevent KEYCODE_APP_SWITCH")
        execute(f"adb {DEVICE} shell input keyevent KEYCODE_APP_SWITCH")

# ─── MAIN FLOW ─────────────────────────────────────────────────────────────────
def main():
    os.system("")  # ANSI on Windows
    get_screen_size()

    # Launch both apps
    launch(NOVO_APP); sleep(5)
    launch(MOCK_APP); sleep(7)
    warn("Scraping mock location UI…")

    root = dump_ui()
    boxes = find_checkboxes(root)
    # first two unchecked → check; rest checked → uncheck
    for i, cb in enumerate(boxes):
        if (i < 2 and not cb["checked"]) or (i >= 2 and cb["checked"]):
            tap(*cb["center"])

    # select current trip
    elems = [e for e in find_clickables(root) if e["text"]]
    if elems:
        tap(*sorted(elems, key=lambda e: e["y"])[0]["center"])
    else:
        err("No clickable elements with text found.")

    # choose right option--update with find text later
    sleep(1)
    root = dump_ui()
    clicks = find_clickables(root)
    if len(clicks) >= 4:
        tap(*sorted(clicks, key=lambda e: -e["y"])[3]["center"])
    else:
        err("Not enough clickable elements.")

    # start trip
    root = dump_ui()
    for n in root.iter("node"):
        if n.attrib.get("text", "").strip() == "Start":
            x1, y1, x2, y2 = parse_bounds(n.attrib["bounds"])
            tap((x1+x2)//2, (y1+y2)//2)
            break
    else:
        err("Start button not found.")

    sleep(0.5)
    ensure_app_focus(NOVO_APP)
    sleep(3)

    # trip control
    root = dump_ui()
    for e in find_clickables(root):
        if e["text"].lower() == "start drive":
            tap(*e["center"])
            warn("Trip simulation running…")
            sleep(300)  # simulate trip
            tap(*e["center"])
            warn("Trip ended.")
            break
    else:
        err("Drive control not found.")

if __name__ == "__main__":
    main()

# heartbeat at 2025-06-16 17:28:25.872302

# heartbeat at 2025-06-16 17:29:02.611857
