import os
import re
import json
import logging
import threading
import time
from datetime import datetime
from dateutil import parser as date_parser

script_dir = os.path.dirname(os.path.abspath(__file__))
REMINDERS_FILE = os.path.join(script_dir, "reminders.json")
logger = logging.getLogger("JarvisReminders")

_lock = threading.Lock()


def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading reminders: {e}")
        return []


def save_reminders(data):
    try:
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving reminders: {e}")


def add_reminder(command):
    try:
        cmd = command.strip()
        cmd_lower = cmd.lower()

        task, time_str = None, None

        # Pattern 1: "... (to/that/for) <task> at <time>"
        m1 = re.search(r"(?:remind me|set a reminder|set an alarm|set alarm|reminder|alarm)\s+(?:to|that|for)?\s*(.+?)\s+at\s+(.+)", cmd_lower)
        if m1:
            task = m1.group(1).strip()
            time_str = m1.group(2).strip()
        else:
            # Pattern 2: "... at <time> (to/that/for) <task>"
            m2 = re.search(r"(?:remind me|set a reminder|set an alarm|set alarm|reminder|alarm)\s+at\s+(.+?)\s+(?:to|that|for)\s+(.+)", cmd_lower)
            if m2:
                time_str = m2.group(1).strip()
                task = m2.group(2).strip()
            else:
                # Pattern 3: "... (to/for) <task> <time>" (e.g. "remind me to call John 5pm")
                m3 = re.search(r"(?:remind me|set a reminder|set an alarm|set alarm|reminder|alarm)\s+(?:to|that|for)?\s*(.+?)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))", cmd_lower)
                if m3:
                    task = m3.group(1).strip()
                    time_str = m3.group(2).strip()

        if not task or not time_str:
            # Fallback: extract time substring
            time_match = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", cmd_lower)
            if time_match:
                time_str = time_match.group(1).strip()
                clean_cmd = re.sub(r"(?:remind me|set a reminder|set an alarm|set alarm|reminder|alarm|remind|at|to|that|for)", "", cmd_lower, flags=re.IGNORECASE)
                clean_cmd = clean_cmd.replace(time_str, "").strip()
                task = clean_cmd if clean_cmd else "your scheduled task"

        if not task or not time_str:
            return "Please phrase your reminder like: 'remind me to <task> at <time>' or 'set alarm to <task> at <time>'."

        try:
            when = date_parser.parse(time_str, fuzzy=True)
            if when < datetime.now():
                when = when.replace(day=when.day + 1)
        except (ValueError, OverflowError) as e:
            logger.warning(f"Could not parse reminder time '{time_str}': {e}")
            return f"I couldn't understand the time '{time_str}'."

        with _lock:
            reminders = load_reminders()
            reminders.append({
                "task": task,
                "time": when.isoformat(),
                "done": False
            })
            save_reminders(reminders)

        return f"Got it — I'll remind you to {task} at {when.strftime('%I:%M %p')}."
    except Exception as e:
        logger.error(f"Error adding reminder for command '{command}': {e}")
        return f"Failed to add reminder: {e}"


def get_reminders():
    reminders = load_reminders()
    upcoming = [r for r in reminders if not r.get("done")]
    if not upcoming:
        return "You have no upcoming reminders."
    formatted = "\n".join(
        f"{i+1}. {r['task']} at {datetime.fromisoformat(r['time']).strftime('%I:%M %p')}"
        for i, r in enumerate(upcoming)
    )
    return f"Here are your reminders:\n{formatted}"


def check_due_reminders():
    due = []
    with _lock:
        reminders = load_reminders()
        now = datetime.now()
        changed = False
        for r in reminders:
            if not r.get("done") and datetime.fromisoformat(r["time"]) <= now:
                due.append(r)
                r["done"] = True
                changed = True
        if changed:
            save_reminders(reminders)
    return due


def start_background_checker(on_due):
    def loop():
        while True:
            try:
                for reminder in check_due_reminders():
                    on_due(reminder)
            except Exception as e:
                logger.error(f"Error in reminder background checker: {e}")
            time.sleep(20)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()