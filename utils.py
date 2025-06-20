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
directory = "C:\\Users\\yufanw\\Downloads"
ANSI = {
    "HEAD": "\033[95m",
    "B": "\033[94m",
    "G": "\033[92m",
    "R": "\033[91m",
    "Y": "\033[33m",
    "END": "\033[0m",
}

device = ""

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