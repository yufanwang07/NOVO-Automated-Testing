import subprocess
import xml.etree.ElementTree as ET
import re
import os
import time
from faker import Faker
import http.client
import json
import random
import hashlib
from pathlib import Path
from datetime import datetime
from agentic_runner import run_agentic


def hash_page(xml_str):
    return hashlib.md5(xml_str.encode()).hexdigest()

blacklist_texts = {
    "faqs", "terms of use", "privacy policy", "telematics policy", "log out"
}

import google.generativeai as genai

# Load Gemini API Key
with open("api.key", "r") as f:
    genai.configure(api_key=f.read().strip())

# Create Gemini model
gemini_model = genai.GenerativeModel("gemini-2.5-flash")


device = ""
directory = "C:\\Users\\yufanw\\Downloads"
faker = Faker()
visited_pages = {}  # hash -> {'xml': str, 'clickables': [(text, bounds)]}
clicked_on = {}     # hash -> set of bounds
log_path = "incidents.log"
info = "The user has name \"Yufan Wang\" with email address yufanw@telenav.com. They have 4 out of 5 trips completed with 19 completed miles. The user has set up permissions and connected a tester bluetooth device vehicle named \"Yufan\'s Airpods Pro\""           # optionally set this string before running
os.system("")  # enables ansi escape characters in terminal

def analyze_with_gemini(page_xml, info_string=""):
    prompt = f"""You are analyzing an Android UI hierarchy in XML format.
Here is some background user/app info (may be irrelevant): {info_string}

This is the current UI page structure:
{page_xml}

Instructions:
- List any errors or oddities you can detect from the XML. 
- Are there likely typos, spacing issues, or missing/blank fields?
- Are there visible error messages or warnings?

Ignore NAF, conventions, design issues, QoL test issues, empty back buttons, weird z layering, disabled buttons, clickables with no text. If a text element seems to be clickable or something similar for no reason, point it out. Respond in a concise list only without any other text, describing the element clearly without too much analysis of the reason. If there are no significant issues, respond with an empty message.
"""
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[Gemini ERROR] {str(e)}"

def log_incident(message):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")

ANSI = {
    "HEAD": "\033[95m",
    "B": "\033[94m",
    "G": "\033[92m",
    "R": "\033[91m",
    "Y": "\033[33m",
    "END": "\033[0m",
}

# Define the PowerShell


conn = http.client.HTTPConnection("tripmocksvc.stg-qa.k8s.mypna.com")

account_safety_preset = random.choice([0.02, 0.05, 0.1])

prob_per_mile = {
    "hard_acceleration": 0.05 * account_safety_preset,
    "hard_brake": 0.05 * account_safety_preset,
    "speeding": 0.1 * account_safety_preset,
}
multiplier = {
    "hard_acceleration": 1,
    "hard_brake": 1,
    "speeding": 1,
}

bay_area_coords = [
    # San Francisco
    (37.774929, -122.419416),  # SF - Civic Center
    (37.807999, -122.417743),  # SF - Fisherman's Wharf
    (37.759703, -122.428093),  # SF - Mission District
    (37.802139, -122.41874),   # SF - North Beach

    # Peninsula
    (37.441883, -122.143019),  # Palo Alto
    (37.457409, -122.170292),  # Menlo Park
    (37.562991, -122.325525),  # San Mateo
    (37.486316, -122.232523),  # Redwood City
    (37.600869, -122.391675),  # SFO Airport

    # South Bay
    (37.386050, -122.083850),  # Mountain View
    (37.331820, -122.030710),  # Cupertino
    (37.354107, -121.955238),  # Santa Clara
    (37.341414, -121.893005),  # Downtown San Jose

    # East Bay
    (37.804363, -122.271111),  # Oakland
    (37.871593, -122.272743),  # Berkeley
    (37.765207, -122.241635),  # Alameda
    (37.695111, -122.126495),  # Hayward
    (37.702152, -121.935791),  # Dublin
    (37.668820, -122.080796),  # Fremont
    (37.783460, -122.211460),  # San Leandro
]

bay_area_coords = [
    (37.386050, -122.083850),  # Mountain View
    (37.386050, -121.957724)   # Sunnyvale
]

def distance_miles(lat1, lon1, lat2, lon2):
    dlat = (lat2 - lat1) * 69.0
    dlon = (lon2 - lon1) * 55.5
    return (dlat**2 + dlon**2) ** 0.5

def generate_events(distance_miles, eff=prob_per_mile):
    return {
        event: sum(random.random() < prob for prob in [eff[event]] * int(distance_miles) * multiplier[event])
        for event in prob_per_mile
    }

def tap(x, y):
    execute(f"adb {device}shell input tap " + str(x) + " " + str(y))
    time.sleep(0.5)

def execute(cmd, silent=False):
    print(" > ", ANSI["G"] + cmd + ANSI["END"])
    try:
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True
        )
        if not silent:
            formatted_output = "\n".join(" |  " + line for line in result.stdout.strip().splitlines())
            if formatted_output != "" and formatted_output != " ":
                print(formatted_output)
        else:
            print(" | ... output trimmed ..." + ANSI["END"])
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_output = "\n".join(" |  " + line for line in e.stderr.strip().splitlines())
        print(ANSI["R"] + "Error:\n" + error_output + ANSI["END"])
        return e.stderr

def sleep(t):
    print(ANSI["Y"] + " |  waiting for " + str(t) + " seconds" + ANSI["END"])
    time.sleep(t)

def warn(text):
    print(ANSI["Y"] + " |  " + text + ANSI["END"])
def err(text):
    print(ANSI["R"] + " !  " + text + ANSI["END"])

def ask():
    return input(ANSI["HEAD"] + ">>  " + ANSI["END"])

def find_node_by_text(text_substring:str, root, ignore_space=False):
    if ignore_space: text_substring = text_substring.replace(" ", "")
    for node in root.iter("node"):
        text = node.attrib.get("text", "").strip()
        if ignore_space: text = text.replace(" ", "")
        if text_substring.lower() == text.lower():
            return node
    return None
def find_button_by_text(text_substring, root):
    for node in root.iter("node"):
        text = node.attrib.get("text", "").strip()
        if text_substring.lower() == text.lower() and node.attrib.get("clickable", "false") == "true":
            return node
    return None

def find_node_with_text(text_substring, root):
    for node in root.iter("node"):
        text = node.attrib.get("text", "").strip()
        if text_substring.lower() in text.lower():
            return node
    return None

def get_center_from_bounds(bounds):
    match = re.match(r"\[(\d+),(\d+)]\[(\d+),(\d+)]", bounds)
    if match:
        x1, y1, x2, y2 = map(int, match.groups())
        return (x1 + x2) // 2, (y1 + y2) // 2
    return None

devices_raw = execute("adb devices")

lines = devices_raw.strip().splitlines()[1:]
valid_devices = [
    line.split()[0]
    for line in lines
    if len(line.split()) >= 2 and line.split()[1] == "device"
]

if len(valid_devices) == 1:
    warn("Defaulting to " + valid_devices[0])
    device = "-s " + valid_devices[0] + " "
elif len(valid_devices) > 1:
    err("Multiple devices detected. Please enter the device ID:")
    device = "-s " + ask().strip() + " "
else:
    err("Fatal error: no online devices found. Fast adb will not work.")
    device = ""



switch = f"adb {device}shell input keyevent KEYCODE_APP_SWITCH"
activity = f"adb {device}shell am start -n "
launch = f"adb {device}shell monkey -p "
novoID = "com.novo.insurance.client"
mockLocationID = "com.telenav.mocklocation"

while (True):
    cmdo = ask().strip()
    cmd = cmdo.lower()
    args = cmd.split(" ")

    if cmd == "novo":
        execute(launch + novoID + " 1")

    elif cmd == "mocklocation":
        execute(launch + mockLocationID + " 1")

    elif cmd == "size":
        execute(f"adb {device}shell wm size")

    elif cmd == "switch":
        execute(switch)
        sleep(0.5)
        execute(switch)

    elif cmd == "clear":
        # Clear app data for Novo
        warn("Will clear app data for Novo, continue?")
        temp = ask()
        if temp.strip().lower() in ["y", "yes", "ye"]:
            execute(f"adb {device}shell pm clear {novoID}")

    elif cmd == "home":
        # Simulate pressing the home button
        execute(f"adb {device}shell input keyevent KEYCODE_HOME")

    elif cmd == "back":
        execute(f"adb {device}shell input keyevent KEYCODE_BACK")

    elif cmd == "recent":
        execute(f"adb {device}shell input keyevent KEYCODE_APP_SWITCH")

    elif cmd == "screenshot":
        # Save screenshot to device, pull it to local
        execute(f"adb {device}shell screencap -p /sdcard/screen.png")
        execute(f"adb {device}pull /sdcard/screen.png {directory}")

    elif cmd == "logcat":
        # Print latest logcat output
        execute(f"adb {device}logcat -d | tail -n 50")

    elif cmd == "restart":
        # Restart the device
        execute(f"adb {device}reboot")

    elif cmd == "lsdata":
        execute(f"adb {device}shell ls /data/data/{novoID}")

    elif cmd == "activity":
        activity_name = ask().strip()
        execute(activity + f"{novoID}/{activity_name}")

    elif cmd == "pull":
        # Pull a file from device (ask for path)
        warn("enter a path")
        path = ask().strip()
        execute(f"adb {device}pull {path} {directory}")

    elif cmd == "push":
        warn("enter filename")
        filename = ask().strip()
        warn("enter dest path")
        dest = ask().strip()
        execute(f"adb {device}push \"{os.path.join(directory, filename)}\" {dest}")

    elif cmd == "input":
        warn("input started")
        text = ask().strip()
        execute(f"adb {device}shell input text \"{text}\"")

    elif cmd == "tap":
        x = ask().strip()
        y = ask().strip()
        tap(int(x), int(y))

    elif cmd == "exit":
        warn("exiting")
        break

    elif cmd == "scrape":
        warn("scrape type? [button/clickable/text]")
        scrape_type = ask().strip().lower()

        # Step 1: Dump the UI hierarchy
        execute(f"adb {device}shell uiautomator dump")

        # Step 2: Get the dump XML
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)

        # Step 3: Parse XML
        root = ET.fromstring(xml_raw)
        elements = []

        if scrape_type in ["button", "clickable"]:
            for node in root.iter("node"):
                cls = node.attrib.get("class", "")
                clickable = node.attrib.get("clickable", "false") == "true"
                if "Button" in cls or "ImageButton" in cls or clickable:
                    text = node.attrib.get("text", "")
                    bounds = node.attrib.get("bounds", "")
                    elements.append((text, bounds))
            if not elements:
                err("No buttons/clickables found.")
            else:
                warn(f"Found {len(elements)} button(s)/clickable(s):")
                for i, (text, bounds) in enumerate(elements, 1):
                    warn(f" {i}. text: [{ANSI['HEAD']}{text or ''}{ANSI['Y']}], bounds: {bounds}{ANSI['END']}")

        elif scrape_type == "text":
            for node in root.iter("node"):
                text = node.attrib.get("text", "")
                if text.strip():  # non-empty text
                    bounds = node.attrib.get("bounds", "")
                    elements.append((text, bounds))
            if not elements:
                err("No text elements found.")
            else:
                warn(f"Found {len(elements)} text element(s):")
                for i, (text, bounds) in enumerate(elements, 1):
                    warn(f" {i}. text: [{ANSI['HEAD']}{text}{ANSI['Y']}], bounds: {bounds}{ANSI['END']}")

        else:
            err("Unknown scrape type. Use 'button', 'clickable', or 'text'.")
    elif len(args) > 0 and args[0] == "generate":
        email = datetime.now().strftime("%m%d.%H%M%S") + "@automation.test"
        if len(args) == 1:
            warn("Email not provided, defaulting to template.")
        elif ".txt" in args[1]:
            err("Bulk generation currently not supported")
            continue
        else:
            email = args[1]

        
        # ----- sequence start: register -----
        execute(f"adb {device}shell pm clear {novoID}")
        sleep(1)
        execute(launch + novoID + " 1")
        execute
        sleep(6)
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        def find_bounds_for_text(text_substring, root=root):
            for node in root.iter("node"):
                text = node.attrib.get("text", "").strip()
                if text.lower() == text_substring.lower():
                    bounds = node.attrib.get("bounds", "")
                    return bounds
            return None

        def parse_bounds(bounds):
            match = re.match(r"\[(\d+),(\d+)]\[(\d+),(\d+)]", bounds)
            if match:
                x1, y1, x2, y2 = map(int, match.groups())
                return (x1 + x2) // 2, (y1 + y2) // 2
            return None

        bounds = find_bounds_for_text("join novo community")
        if not bounds:
            err("Couldn't find 'Join Novo Community' button.")
            continue
        x, y = parse_bounds(bounds)
        tap(x, y)

        sleep(1)

        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)
        bounds = find_bounds_for_text("i am in", root)
        if not bounds:
            err("Couldn't find 'I am in' button.")
            continue
        x, y = parse_bounds(bounds)
        tap(x, y)
        sleep(1)

        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)
        bounds = find_bounds_for_text("enter your email to sign up", root)
        if not bounds:
            err("Couldn't find email input field.")
            continue

        x, y = parse_bounds(bounds)
        tap(x, y)

        execute(f"adb {device}shell input text \"{email}\"")
        bounds = find_bounds_for_text("continue", root)
        if not bounds:
            err("Couldn't find 'Continue' button.")
            continue
        x, y = parse_bounds(bounds)
        tap(x, y)

        


        # ----- verification code -----
        sleep(2)
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        node = find_node_by_text("verification code", root)

        if node == None:
            cont_node = find_node_by_text("continue", root)
            if cont_node == None:
                err("Couldn't find fallback 'Continue' button.")
                continue
            cont_bounds = cont_node.attrib.get("bounds", "")
            coords = get_center_from_bounds(cont_bounds)
            if coords:
                tap(*coords)
                sleep(2)

            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)
            node = find_node_by_text("verification code", root)

        if node == None:
            err("Couldn't find 'Verification code' field.")
            continue

        bounds = node.attrib.get("bounds", "")
        coords = get_center_from_bounds(bounds)
        tap(*coords)

        execute(f"adb {device}shell input keyevent 279")  # KEYCODE_PASTE

        checkboxes = []
        for node in root.iter("node"):
            if node.attrib.get("checkable", "") == "true":
                checked = node.attrib.get("checked", "") == "false"
                if checked:
                    cb_bounds = node.attrib.get("bounds", "")
                    cb_coords = get_center_from_bounds(cb_bounds)
                    if cb_coords:
                        checkboxes.append(cb_coords)

        if checkboxes:
            for coords in checkboxes:
                tap(*coords)
                sleep(0.2)
        
        cont_node = find_node_by_text("continue", root)
        if cont_node == "None":
            err("Couldn't find final 'Continue' button.")
            continue
        cont_bounds = cont_node.attrib.get("bounds", "")
        coords = get_center_from_bounds(cont_bounds)
        tap(*coords)

        # --- first/last name ---
        sleep(4)
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)
        first_name_node = find_node_by_text("first name", root)
        last_name_node = find_node_by_text("last name", root)
        full_name = ""

        if first_name_node is not None and last_name_node is not None:
            full_name = faker.name()
            warn(f"Generated name: {full_name}")
            while "." in full_name:
                err("Formatting error. Regenerating.")
                full_name = faker.name()
                warn(f"Generated name: {full_name}")
            if full_name:
                parts = full_name.split()
                first = parts[0]
                last = parts[-1] if len(parts) > 1 else ""

                # Tap and input first name
                bounds = first_name_node.attrib.get("bounds", "")
                coords = get_center_from_bounds(bounds)
                tap(*coords)
                execute(f"adb {device}shell input text \"{first}\"")
                sleep(0.5)

                # Tap and input last name
                bounds = last_name_node.attrib.get("bounds", "")
                coords = get_center_from_bounds(bounds)
                tap(*coords)
                execute(f"adb {device}shell input text \"{last}\"")
                sleep(0.5)

                cont_node = find_node_by_text("continue", root)
                if cont_node is not None:
                    coords = get_center_from_bounds(cont_node.attrib.get("bounds", ""))
                    tap(*coords)
                else:
                    err("Couldn't find 'Continue' after name entry.")
            else:
                skip_node = find_node_by_text("skip", root)
                if skip_node:
                    coords = get_center_from_bounds(skip_node.attrib.get("bounds", ""))
                    tap(*coords)
                else:
                    err("No name entered and no 'Skip' button found.")
        else:
            err("Name fields not found")
            
        # --- address entry ---
        sleep(1)
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        address_node = find_node_with_text("address", root)
        if address_node is not None:
            bounds = address_node.attrib.get("bounds", "")
            coords = get_center_from_bounds(bounds)

            tap(*coords)
            house_number = str(random.randint(10, 9999))
            warn(f"Generated address number: {house_number}")
            execute(f"adb {device}shell input text \"{house_number}\"")

            sleep(3)

            # tap 200 pixels below the address field, approximate location since scraping doesn't work
            tap(coords[0], coords[1] + 200)
            sleep(3)

            cont_node = find_node_by_text("continue", root)
            if cont_node is not None:
                cont_bounds = cont_node.attrib.get("bounds", "")
                cont_coords = get_center_from_bounds(cont_bounds)
                tap(*cont_coords)
            else:
                err("Continue button not found after address entry.")
        else:
            err("Address field not found.")


        
        sleep(4)
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)
        skip = find_node_by_text("skip for now", root)
        if skip is not None:
            bounds = skip.attrib.get("bounds", "")
            coords = get_center_from_bounds(bounds)
            tap(*coords)
        else:
            err("Fatal error, could not skip permissions")

        def pair():
            # --- Finish Setup ---
            sleep(2)

            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)

            finish_node = find_node_by_text("finish setup", root)
            if finish_node is not None:
                bounds = finish_node.attrib.get("bounds", "")
                coords = get_center_from_bounds(bounds)
                tap(*coords)
                
                sleep(1)
                
                execute(f"adb {device}shell uiautomator dump")
                xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
                root = ET.fromstring(xml_raw)
            else:
                err("Dashboard check failed, assuming vehicle setup.")

            yes_node = find_button_by_text("start setup", root)
            if yes_node is not None:
                bounds = yes_node.attrib.get("bounds", "")
                coords = get_center_from_bounds(bounds)
                tap(*coords)
                sleep(0.5)
            else:
                err("Auto-start detected, assuming entry through dashboard")

            while True:
                execute(f"adb {device}shell uiautomator dump")
                xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
                root = ET.fromstring(xml_raw)

                yes_node = find_node_by_text("yes", root)
                if yes_node is not None:
                    bounds = yes_node.attrib.get("bounds", "")
                    coords = get_center_from_bounds(bounds)
                    tap(*coords)
                    sleep(0.5)
                else:
                    break
        
        pair()
        sleep(1)

        # --- Permissions Fix via "Go to Settings" ---
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        goto_settings_node = find_node_by_text("go to settings", root)
        if goto_settings_node is not None:
            err("Insufficient permissions. Attempting a fix...")
            coords = get_center_from_bounds(goto_settings_node.attrib.get("bounds", ""))
            tap(*coords)
            sleep(1)

            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)
            permissions_node = find_node_by_text("permissions", root)
            if permissions_node is not None:
                coords = get_center_from_bounds(permissions_node.attrib.get("bounds", ""))
                tap(*coords)
            sleep(1)

            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)
            nearby_node = find_node_by_text("nearby devices", root)
            if nearby_node is not None:
                coords = get_center_from_bounds(nearby_node.attrib.get("bounds", ""))
                tap(*coords)
            sleep(1)

            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)
            allow_node = find_node_by_text("allow", root)
            if allow_node is not None:
                coords = get_center_from_bounds(allow_node.attrib.get("bounds", ""))
                tap(*coords)

            all_nodes = list(root.iter("node"))
            top_left_node = min(all_nodes, key=lambda n: sum(get_center_from_bounds(n.attrib.get("bounds", "000,000][000,000"))))
            coords = get_center_from_bounds(top_left_node.attrib.get("bounds", ""))
            for _ in range(3):
                tap(*coords)

        pair()
        sleep(1)

        size_raw = execute(f"adb {device}shell wm size", silent=True)
        match = re.search(r'Physical size: (\d+)x(\d+)', size_raw)
        if match:
            width, height = int(match[1]), int(match[2])
            x = width // 2
            for y in range(height // 3, height - 200, 100):
                execute(f"adb {device}shell input tap {x} {y}")
        else:
            err("Could not determine screen size.")
        
        sleep(3)

        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        screen_size_raw = execute(f"adb {device}shell wm size")
        match = re.search(r'Physical size: (\d+)x(\d+)', screen_size_raw)
        if match:
            width, height = int(match[1]), int(match[2])
        else:
            width, height = 1080, 1920  # fallback defaults

        all_nodes = list(root.iter("node"))
        top_right_node = min(
            all_nodes,
            key=lambda n: (
                coords := get_center_from_bounds(n.attrib.get("bounds", "0,0][0,0")),
                width - coords[0] + coords[1]
            )[1]
        )
        coords = get_center_from_bounds(top_right_node.attrib.get("bounds", ""))
        execute(f"adb {device}shell input tap {coords[0]} {coords[1]}")

        sleep(2)

        # Profile
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        name_node = find_node_by_text(full_name, root, True)
        if name_node is not None:
            coords = get_center_from_bounds(name_node.attrib.get("bounds", ""))

            # secret setting
            execute(f"adb {device}shell input swipe {coords[0]} {coords[1]} {coords[0]} {coords[1]} 700", silent=True)
            for _ in range(3):
                execute(f"adb {device}shell input tap {coords[0]} {coords[1]}", silent=True)
            execute(f"adb {device}shell input swipe {coords[0]} {coords[1]} {coords[0]} {coords[1]} 700", silent=True)

        else:
            err(f"Could not find a button with text '{full_name}'.")


        sleep(1)
        
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
        root = ET.fromstring(xml_raw)

        text_elements = []
        for node in root.iter("node"):
            text = node.attrib.get("text", "").strip()
            bounds = node.attrib.get("bounds", "")
            if text:
                text_elements.append((text, bounds))

        # scrape UID and CID
        TUID = None
        CCID = None
        for i, (text, _) in enumerate(text_elements):
            if text.lower() == "telematic user id" and i + 1 < len(text_elements):
                TUID = text_elements[i + 1][0]
            if text.lower() == "channel client id 1" and i + 1 < len(text_elements):
                CCID = text_elements[i + 1][0]

        if TUID:
            warn(f"Telematic User ID found: {ANSI['HEAD']}{TUID}{ANSI['END']}")
        else:
            err("Telematic User ID not found.")

        if CCID:
            warn(f"Channel Client ID found: {ANSI['HEAD']}{CCID}{ANSI['END']}")
        else:
            err("Channel Client ID not found.")
        
        all_nodes = list(root.iter("node"))
        top_left_node = min(all_nodes, key=lambda n: sum(get_center_from_bounds(n.attrib.get("bounds", "000,000][000,000"))))
        coords = get_center_from_bounds(top_left_node.attrib.get("bounds", ""))
        tap(*coords)


        total = 0
        for i in range(5):
            start_coord, end_coord = random.sample(bay_area_coords, 2)
            distance = distance_miles(*start_coord, *end_coord)
            total += distance

            if i == 4 and total < 180:
                end_coord = 36.737232, -119.784912
                total -= distance
                distance = distance_miles(*start_coord, *end_coord)
                total += distance
            trip_start_time_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            event_counts = generate_events(distance)

            payload = json.dumps({
                "desired_trips": [
                    {
                        "mock_vin": CCID,
                        "mock_telematics_user_id": TUID,
                        "trip_start_point": f"{start_coord[0]},{start_coord[1]}",
                        "trip_end_point": f"{end_coord[0]},{end_coord[1]}",
                        "trip_start_time_local": trip_start_time_local,
                        "job_creator": "TTTEST",
                        "target_trip_format": "pipeline-novo_mobile_bt",
                        "desired_drive_events": event_counts,
                        "job_options": {
                            "match_device_id": CCID
                        }
                    }
                ]
            })

            headers = {
            'Content-Type': 'application/json'
            }

            conn.request("POST", "/mock/trip/rapid", payload, headers)
            res = conn.getresponse()
            data = res.read()
            print(ANSI["HEAD"] + " |  Successfully mocked trip " + str(i + 1) + f" for ~{distance * 1.3} miles" )
            time.sleep(1)
        
        print(ANSI["HEAD"] + f" |  Expected mocked distance: {total} miles")
        sleep(1)

        tap(*coords)

    elif cmd == "sweep":
        pass

    elif args[0] == "mocktrip":
        warn("TUID not provided. Press enter to default to preset.")
        TUID = ask()
        if len(TUID) < 10:
            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)

            screen_size_raw = execute(f"adb {device}shell wm size")
            match = re.search(r'Physical size: (\d+)x(\d+)', screen_size_raw)
            if match:
                width, height = int(match[1]), int(match[2])
            else:
                width, height = 1080, 1920  # fallback defaults

            all_nodes = list(root.iter("node"))
            top_right_node = min(
                all_nodes,
                key=lambda n: (
                    coords := get_center_from_bounds(n.attrib.get("bounds", "0,0][0,0")),
                    width - coords[0] + coords[1]
                )[1]
            )
            coords = get_center_from_bounds(top_right_node.attrib.get("bounds", ""))
            execute(f"adb {device}shell input tap {coords[0]} {coords[1]}")

            sleep(2)
            # Profile
            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)

            name_node = find_node_with_text("  ", root)
            if name_node is not None:
                coords = get_center_from_bounds(name_node.attrib.get("bounds", ""))

                # secret setting
                execute(f"adb {device}shell input swipe {coords[0]} {coords[1]} {coords[0]} {coords[1]} 700", silent=True)
                for _ in range(3):
                    execute(f"adb {device}shell input tap {coords[0]} {coords[1]}", silent=True)
                execute(f"adb {device}shell input swipe {coords[0]} {coords[1]} {coords[0]} {coords[1]} 700", silent=True)

            else:
                err(f"Could not find a button with text '  '.")


            sleep(1)
            
            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)

            text_elements = []
            for node in root.iter("node"):
                text = node.attrib.get("text", "").strip()
                bounds = node.attrib.get("bounds", "")
                if text:
                    text_elements.append((text, bounds))

            # scrape UID and CID
            TUID = None
            CCID = None
            for i, (text, _) in enumerate(text_elements):
                if text.lower() == "telematic user id" and i + 1 < len(text_elements):
                    TUID = text_elements[i + 1][0]
                if text.lower() == "channel client id 1" and i + 1 < len(text_elements):
                    CCID = text_elements[i + 1][0]

            if TUID:
                warn(f"Telematic User ID found: {ANSI['HEAD']}{TUID}{ANSI['END']}")
            else:
                err("Telematic User ID not found.")

            if CCID:
                warn(f"Channel Client ID found: {ANSI['HEAD']}{CCID}{ANSI['END']}")
            else:
                err("Channel Client ID not found.")
            
            all_nodes = list(root.iter("node"))
            top_left_node = min(all_nodes, key=lambda n: sum(get_center_from_bounds(n.attrib.get("bounds", "000,000][000,000"))))
            coords = get_center_from_bounds(top_left_node.attrib.get("bounds", ""))
            tap(*coords)
        else:
            warn("CCID not provided. Press enter to default to preset.")
            CCID = ask()
            if len(CCID) < 10:            # Profile
                execute(f"adb {device}shell uiautomator dump")
                xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
                root = ET.fromstring(xml_raw)

                screen_size_raw = execute(f"adb {device}shell wm size")
                match = re.search(r'Physical size: (\d+)x(\d+)', screen_size_raw)
                if match:
                    width, height = int(match[1]), int(match[2])
                else:
                    width, height = 1080, 1920  # fallback defaults

                all_nodes = list(root.iter("node"))
                top_right_node = min(
                    all_nodes,
                    key=lambda n: (
                        coords := get_center_from_bounds(n.attrib.get("bounds", "0,0][0,0")),
                        width - coords[0] + coords[1]
                    )[1]
                )
                coords = get_center_from_bounds(top_right_node.attrib.get("bounds", ""))
                execute(f"adb {device}shell input tap {coords[0]} {coords[1]}")

                sleep(2)
                execute(f"adb {device}shell uiautomator dump")
                xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
                root = ET.fromstring(xml_raw)
                name_node = find_node_with_text("  ", root)
                if name_node is not None:
                    coords = get_center_from_bounds(name_node.attrib.get("bounds", ""))

                    # secret setting
                    execute(f"adb {device}shell input swipe {coords[0]} {coords[1]} {coords[0]} {coords[1]} 700", silent=True)
                    for _ in range(3):
                        execute(f"adb {device}shell input tap {coords[0]} {coords[1]}", silent=True)
                    execute(f"adb {device}shell input swipe {coords[0]} {coords[1]} {coords[0]} {coords[1]} 700", silent=True)

                else:
                    err(f"Could not find a button with text '  '.")


                sleep(1)
                
                execute(f"adb {device}shell uiautomator dump")
                xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
                root = ET.fromstring(xml_raw)

                text_elements = []
                for node in root.iter("node"):
                    text = node.attrib.get("text", "").strip()
                    bounds = node.attrib.get("bounds", "")
                    if text:
                        text_elements.append((text, bounds))

                # scrape UID and CID
                TUID = None
                CCID = None
                for i, (text, _) in enumerate(text_elements):
                    if text.lower() == "telematic user id" and i + 1 < len(text_elements):
                        TUID = text_elements[i + 1][0]
                    if text.lower() == "channel client id 1" and i + 1 < len(text_elements):
                        CCID = text_elements[i + 1][0]

                if TUID:
                    warn(f"Telematic User ID found: {ANSI['HEAD']}{TUID}{ANSI['END']}")
                else:
                    err("Telematic User ID not found.")

                if CCID:
                    warn(f"Channel Client ID found: {ANSI['HEAD']}{CCID}{ANSI['END']}")
                else:
                    err("Channel Client ID not found.")
                
                all_nodes = list(root.iter("node"))
                top_left_node = min(all_nodes, key=lambda n: sum(get_center_from_bounds(n.attrib.get("bounds", "000,000][000,000"))))
                coords = get_center_from_bounds(top_left_node.attrib.get("bounds", ""))
                tap(*coords)
        account_safety_preset = random.choice([0.1, 0.4, 1.0])
        if len(args) > 1:
            account_safety_preset = int(args[1])
        warn(f"Running mock trip with danger level {account_safety_preset}")
        prob_per_mile = {
            "hard_acceleration": 0.05 * account_safety_preset,
            "hard_brake": 0.05 * account_safety_preset,
            "speeding": 0.1 * account_safety_preset,
        }
        start_coord, end_coord = random.sample(bay_area_coords, 2)
        distance = distance_miles(*start_coord, *end_coord)
        trip_start_time_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_counts = generate_events(distance, prob_per_mile)

        payload = json.dumps({
            "desired_trips": [
                {
                    "mock_vin": CCID,
                    "mock_telematics_user_id": TUID,
                    "trip_start_point": f"{start_coord[0]},{start_coord[1]}",
                    "trip_end_point": f"{end_coord[0]},{end_coord[1]}",
                    "trip_start_time_local": trip_start_time_local,
                    "job_creator": "TTTEST",
                    "target_trip_format": "pipeline-novo_mobile_bt",
                    "desired_drive_events": event_counts,
                    "job_options": {
                        "match_device_id": CCID
                    }
                }
            ]
        })

        headers = {
        'Content-Type': 'application/json'
        }

        conn.request("POST", "/mock/trip/rapid", payload, headers)
        res = conn.getresponse()
        data = res.read()
        print(ANSI["HEAD"] + f" |  Successfully mocked trip for ~{distance * 1.3} miles" )

    elif cmd == "verify":
        while True:
            execute(f"adb {device}shell uiautomator dump")
            xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            root = ET.fromstring(xml_raw)

            page_hash = hash_page(xml_raw)
            if page_hash in visited_pages:
                warn("Seen this page before. Skipping re-analysis.")
            else:
                # Scrape clickables
                # Scrape clickables (filtered)
                clickables = []
                for node in root.iter("node"):
                    cls = node.attrib.get("class", "")
                    clickable = node.attrib.get("clickable", "false") == "true"
                    bounds = node.attrib.get("bounds", "")
                    text = node.attrib.get("text", "").strip().lower()
                    if clickable and "link" not in cls.lower():
                        if any(bad in text for bad in blacklist_texts):
                            continue  # skip blacklisted elements
                        clickables.append((text, bounds))

                visited_pages[page_hash] = {
                    "xml": xml_raw,
                    "clickables": clickables
                }
                clicked_on[page_hash] = set()
                # Analyze
                issues = analyze_with_gemini(xml_raw, info)
                log_incident(f"Page {page_hash} analyzed.\n{issues}")

            # Click a random unclicked clickable
            clickables = visited_pages[page_hash]["clickables"]
            unclicked = [b for t, b in clickables if b not in clicked_on[page_hash]]
            if not unclicked:
                warn("All clickables clicked on this page.")
                break

            chosen = random.choice(unclicked)
            clicked_on[page_hash].add(chosen)

            coords = get_center_from_bounds(chosen)
            tap(*coords)

            # New page dump
            time.sleep(1)
            execute(f"adb {device}shell uiautomator dump")
            new_xml = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)
            if hash_page(new_xml) == page_hash:
                log_incident(f"Non-functional clickable detected on page {page_hash}:\nBounds: {chosen}\nNo page change.")
            else:
                warn("Navigated to new page.")

    elif cmd == "agentic":
        run_agentic(device, directory)

    else:
        execute(cmdo)
