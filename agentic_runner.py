import json
import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ValidationError
from utils import execute, tap, sleep, warn, err
from google import genai

agent = None
with open("api.key", "r") as f:
    agent = genai.Client(api_key=f.read().strip())
    assistant = genai.Client(api_key=f.read().strip())


ANSI = {
    "HEAD": "\033[95m",
    "B": "\033[94m",
    "G": "\033[92m",
    "R": "\033[91m",
    "Y": "\033[33m",
    "END": "\033[0m",
}

class AgenticResponse(BaseModel):
    command_type: str  # tap, input, paste, other, help, wait
    x: Optional[int] = None
    y: Optional[int] = None
    content: Optional[str] = None
    explanation: Optional[str] = None

def init_log_file():
    os.makedirs("agent_logs", exist_ok=True)
    now = datetime.now()
    filename = now.strftime("agent_logs/agent_%m%d.%H%M.log")
    return open(filename, "w", encoding="utf-8")

def log(log_file, message):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    log_file.write(f"{timestamp} {message}\n")
    log_file.flush()  # Ensure it's written to disk immediately

def run_assistant(device, directory, log_file, help, goal):
    warn(f"Starting agentic assistant for goal: {goal}")
    
    last = None
    execute(f"adb {device}shell screencap -p /sdcard/agentic_screen.png")
    execute(f"adb {device}pull /sdcard/agentic_screen.png {directory}")

    # UI dump
    execute(f"adb {device}shell uiautomator dump")
    xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)

    # Gemini prompt
    prompt = f"""
You are assisting in automating Android UI interactions to achieve the following goal:
"{goal}"

Here is the UI XML dump:
{xml_raw}

Strictly respond ONLY in this JSON format:
  "command_type": "tap" | "input" | "paste" | "other" | "help" | "wait" | "success",
  "x": optional int (required if tap),
  "y": optional int (required if tap),
  "content": optional string (required if input, paste, or other). Note if you're trying to input text with spaces, put a \\ before the space as adb commands require this to type a space.
  "explanation": brief description of what you just tried to do
No explanation or extra text. Tap will tap at coordinates x, y. Input will type in the content, if an input field is selected. Paste will paste off clipboard, if an input field is selected. Provide a powershell (probably adb) command in content to run if other. If the screen is loading, you can wait. If you don't know what to do, use help, and provide a reason in content. If you've achieved the goal, return success with a summary of your previous steps in content.
Note some elements may be textfields (likely labeled focusable in json), and you will have to tap them first before entering text.
"""

        if last:
            prompt += f"\n\nHere's what you just tried to do in your last step:\n{last.explanation}Note if you don't see the text you just entered in the XML, you likely have not selected the textfield before typing."

        try:
            response = agent.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': AgenticResponse,
                }
            )
            raw_text = response.text.strip()
            data = json.loads(raw_text)
            agentic_response = AgenticResponse(**data)
            log(log_file, f"AGENT ACTION: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError:
            error_msg = f"Gemini returned invalid JSON: {response.text}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break
        except ValidationError as ve:
            error_msg = f"Response failed schema validation: {ve}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break
        except Exception as e:
            error_msg = f"Gemini ERROR: {str(e)}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break

        last = agentic_response
        ct = agentic_response.command_type

        if ct == "tap":
            if agentic_response.x is not None and agentic_response.y is not None:
                tap(agentic_response.x, agentic_response.y)
                sleep(3)
            else:
                error_msg = "Tap command missing coordinates."
                err(error_msg)
                log(log_file, f"ERROR: {error_msg}")
                break
        elif ct == "input":
            execute(f"adb {device}shell input text \"{agentic_response.content}\"")
            sleep(2)
        elif ct == "paste":
            execute(f"adb {device}shell input keyevent 279")
            sleep(2)
        elif ct == "other":
            execute(agentic_response.content)
        elif ct == "wait":
            sleep(2)
        elif ct == "help":
            msg = f"Agent requested help; reason: {agentic_response.content}"
            err(msg)
            log(log_file, f"ERROR: {msg}")
            break
        elif ct == "success":
            msg = f"Agent marked success; stopping agentic sequence. Summary: {agentic_response.content}"
            print(f"{ANSI["HEAD"]} |  {msg}")
            log(log_file, f"INFO: {msg}")
            break
        else:
            error_msg = f"Unknown command type: {ct}"
            err(error_msg)
            log(log_file, f"AGENT ERROR: {error_msg}")
            break

def run_agent(device, directory):
    log_file = init_log_file()

    goal = input("\033[95m>>  \033[0m").strip()
    warn(f"Starting agentic automation for goal: {goal}")
    log(log_file, f"GOAL: {goal}")
    
    last = None

    while True:
        # Screenshot
        execute(f"adb {device}shell screencap -p /sdcard/agentic_screen.png")
        execute(f"adb {device}pull /sdcard/agentic_screen.png {directory}")

        # UI dump
        execute(f"adb {device}shell uiautomator dump")
        xml_raw = execute(f"adb {device}shell cat /sdcard/window_dump.xml", silent=True)

        # Gemini prompt
        prompt = f"""
You are assisting in automating Android UI interactions to achieve the following goal:
"{goal}"

Here is the UI XML dump:
{xml_raw}

Strictly respond ONLY in this JSON format:
  "command_type": "tap" | "input" | "paste" | "other" | "help" | "wait" | "success",
  "x": optional int (required if tap),
  "y": optional int (required if tap),
  "content": optional string (required if input, paste, or other). Note if you're trying to input text with spaces, put a \\ before the space as adb commands require this to type a space.
  "explanation": brief description of what you just tried to do
No explanation or extra text. Tap will tap at coordinates x, y. Input will type in the content, if an input field is selected. Paste will paste off clipboard, if an input field is selected. Provide a powershell (probably adb) command in content to run if other. If the screen is loading, you can wait. If you don't know what to do, use help, and provide a reason in content. If you've achieved the goal, return success with a summary of your previous steps in content.
Note some elements may be textfields (likely labeled focusable in json), and you will have to tap them first before entering text.
"""

        if last:
            prompt += f"\n\nHere's what you just tried to do in your last step:\n{last.explanation}Note if you don't see the text you just entered in the XML, you likely have not selected the textfield before typing."

        try:
            response = agent.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': AgenticResponse,
                }
            )
            raw_text = response.text.strip()
            data = json.loads(raw_text)
            agentic_response = AgenticResponse(**data)
            log(log_file, f"ACTION: {json.dumps(data, indent=2)}")
        except json.JSONDecodeError:
            error_msg = f"Gemini returned invalid JSON: {response.text}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break
        except ValidationError as ve:
            error_msg = f"Response failed schema validation: {ve}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break
        except Exception as e:
            error_msg = f"Gemini ERROR: {str(e)}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break

        last = agentic_response
        ct = agentic_response.command_type

        if ct == "tap":
            if agentic_response.x is not None and agentic_response.y is not None:
                tap(agentic_response.x, agentic_response.y)
                sleep(3)
            else:
                error_msg = "Tap command missing coordinates."
                err(error_msg)
                log(log_file, f"ERROR: {error_msg}")
                break
        elif ct == "input":
            execute(f"adb {device}shell input text \"{agentic_response.content}\"")
            sleep(2)
        elif ct == "paste":
            execute(f"adb {device}shell input keyevent 279")
            sleep(2)
        elif ct == "other":
            execute(agentic_response.content)
        elif ct == "wait":
            sleep(2)
        elif ct == "help":
            msg = f"Agent requested help; reason: {agentic_response.content}"
            err(msg)
            log(log_file, f"ERROR: {msg}")
            break
        elif ct == "success":
            msg = f"Agent marked success; stopping agentic sequence. Summary: {agentic_response.content}"
            print(f"{ANSI["HEAD"]} |  {msg}")
            log(log_file, f"INFO: {msg}")
            break
        else:
            error_msg = f"Unknown command type: {ct}"
            err(error_msg)
            log(log_file, f"ERROR: {error_msg}")
            break

    log_file.close()
