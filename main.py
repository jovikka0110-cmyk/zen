import os
import re
import warnings
import logging
import webbrowser
import datetime
import time



# Suppress SDK warnings
warnings.filterwarnings("ignore")
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)

script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'jarvis.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger("JarvisMain")

try:
    import brain
except Exception as e:
    logger.critical(f"Failed to import brain module: {e}")

try:
    import voice
except Exception as e:
    logger.warning(f"Failed to import voice module: {e}")
    voice = None


def get_command():
    """Get input from the user cleanly."""
    try:
        command = input("You: ")
        return command.lower().strip()
    except (KeyboardInterrupt, EOFError):
        raise
    except Exception as e:
        logger.error(f"Error getting command input: {e}")
        return ""


def do_math(command):
    """Extract and safely evaluate a math expression from command."""
    try:
        expression = re.sub(r"[^0-9+\-*/().\s]", "", command).strip()
        if not expression:
            return "I couldn't find a math expression in that."

        # Check for valid digits
        if not any(char.isdigit() for char in expression):
            return "Please provide valid numbers to calculate."

        result = eval(expression)
        return f"That equals {result}."
    except ZeroDivisionError:
        return "Division by zero is not allowed."
    except OverflowError:
        return "That calculation resulted in a number too large to compute."
    except (SyntaxError, TypeError, ValueError, NameError) as e:
        logger.warning(f"Math evaluation expression error: {e}")
        return "Hmm, I couldn't calculate that. Try something like 'calculate 12 * 4'."
    except Exception as e:
        logger.error(f"Unexpected math error: {e}")
        return "Could not perform calculation due to an internal error."


def open_website(command):
    """Open a website based on a keyword in the command, enforcing educational/resource access controls."""
    cmd_lower = command.lower()

    # Blocked Social Media list
    social_media = [
        "instagram", "facebook", "twitter", "x.com", "tiktok", 
        "reddit", "snapchat", "pinterest", "linkedin", "tumblr"
    ]

    for sm in social_media:
        if sm in cmd_lower:
            return f"Access Denied: Social media access ('{sm}') is blocked. Access is granted only to educational and resource websites."

    # Allowed Educational and Resource Websites
    allowed_sites = {
        "google": "https://google.com",
        "github": "https://github.com",
        "wikipedia": "https://wikipedia.org",
        "coursera": "https://coursera.org",
        "khan academy": "https://khanacademy.org",
        "khanacademy": "https://khanacademy.org",
        "stackoverflow": "https://stackoverflow.com",
        "geeksforgeeks": "https://geeksforgeeks.org",
        "gfg": "https://geeksforgeeks.org",
        "w3schools": "https://w3schools.com",
        "arxiv": "https://arxiv.org",
        "chatgpt": "https://chatgpt.com",
        "openai": "https://chatgpt.com",
        "duolingo": "https://duolingo.com",
        "udemy": "https://udemy.com",
        "edx": "https://edx.org",
    }

    try:
        for keyword, url in allowed_sites.items():
            if keyword in cmd_lower:
                webbrowser.open(url)
                return f"Opening educational resource: {keyword.capitalize()} ({url})"
        
        return "Access Restricted: Only educational and learning resource websites (like Google, GitHub, Wikipedia, Khan Academy, Coursera, StackOverflow) are allowed."
    except Exception as e:
        logger.error(f"Error opening browser for command '{command}': {e}")
        return f"Failed to open browser: {e}"


def save_note(command):
    """Save a note to notes.txt and memory.json safely."""
    try:
        note_text = command
        for keyword in ["save note", "write note", "take a note", "note", "remember"]:
            if keyword in note_text:
                note_text = note_text.split(keyword, 1)[-1].strip()
                break

        if not note_text:
            return "What would you like me to note down?"

        notes_file = os.path.join(script_dir, "notes.txt")
        with open(notes_file, "a", encoding="utf-8") as f:
            f.write(note_text + "\n")

        if 'brain' in globals() and hasattr(brain, 'add_fact'):
            brain.add_fact(note_text)

        return f"Saved note to memory: '{note_text}'"
    except Exception as e:
        logger.error(f"Failed to save note: {e}")
        return "Failed to save note due to file issue."


def read_notes(command):
    """Read back all saved notes safely."""
    try:
        notes_file = os.path.join(script_dir, "notes.txt")
        if not os.path.exists(notes_file):
            return "You don't have any notes yet."
        with open(notes_file, "r", encoding="utf-8") as f:
            notes = f.readlines()
        if not notes:
            return "You don't have any notes yet."
        formatted = "\n".join(f"{i+1}. {n.strip()}" for i, n in enumerate(notes) if n.strip())
        return f"Here are your notes:\n{formatted}"
    except FileNotFoundError:
        return "You don't have any notes yet."
    except Exception as e:
        logger.error(f"Failed to read notes: {e}")
        return "Could not read notes at this time."


def respond(command, file_data=None):
    """Process user command and return appropriate reply safely."""
    try:
        cmd_lower = command.lower().strip()

        # Check for exiting Tutor Mode first
        exit_tutor_triggers = ["exit tutor", "stop tutor", "disable tutor", "leave tutor mode", "stop teaching", "exit teacher"]
        if any(trig in cmd_lower for trig in exit_tutor_triggers):
            if 'brain' in globals() and hasattr(brain, 'set_tutor_mode'):
                brain.set_tutor_mode(False)
            return "Exited Tutor Mode. Returned to standard assistant mode."

        # Check for Tutor Mode trigger commands
        tutor_triggers = [
            "turn as jarvis", "turn jarvis", "tutor mode", "start tutor", 
            "teacher mode", "learn programming", "teach me coding", 
            "start teaching", "hands on mode"
        ]
        if any(trig in cmd_lower for trig in tutor_triggers):
            if 'brain' in globals() and hasattr(brain, 'set_tutor_mode'):
                brain.set_tutor_mode(True, topic="programming")
            return (
                "🎓 Tutor Mode Activated! Hello! I'm your friendly Jarvis Programming Tutor. "
                "I'm super excited to teach you programming with hands-on experience! "
                "What language would you like to master today? (e.g. Python, JavaScript, HTML/CSS, C++, Java, SQL)"
            )

        if "remind me" in command or "remaind me" in command:
            import reminders
            return reminders.add_reminder(command)
        elif "my reminders" in command or "show reminders" in command:
            import reminders
            return reminders.get_reminders()

        words = set(re.findall(r'\b\w+\b', cmd_lower))

        if not file_data and any(w in words for w in ["hello", "hi", "hey"]):
            tutor_active, _ = brain.get_tutor_mode() if ('brain' in globals() and hasattr(brain, 'get_tutor_mode')) else (False, "")
            if tutor_active:
                return "Hey there! Ready to write some code today? Tell me which programming concept or language you want to tackle hands-on!"
            return "Hey, I'm online. What do you need?"
        elif not file_data and "time" in words:
            now = datetime.datetime.now().strftime("%I:%M %p")
            return f"It's currently {now}."
        elif not file_data and ("calculate" in words or "math" in words):
            return do_math(command)
        elif not file_data and "open" in words:
            return open_website(command)
        elif not file_data and ("my notes" in command or "read notes" in command):
            return read_notes(command)
        elif not file_data and ("clear memory" in command or "reset memory" in command):
            if 'brain' in globals() and hasattr(brain, 'reset_memory'):
                brain.reset_memory()
            return "Memory wiped clean."
        elif not file_data and ("note" in words or "remember" in words):
            return save_note(command)
        elif command in ["exit", "quit", "bye"]:
            return None

        else:
            if 'brain' in globals() and hasattr(brain, 'think'):
                return brain.think(command, file_data=file_data)
            else:
                return "Brain module not available."
    except Exception as e:
        logger.error(f"Error in respond logic for command '{command}': {e}", exc_info=True)
        return "I encountered an internal error processing that command, but system remains active."




def safe_speak(text):
    if not text:
        return
    if voice and hasattr(voice, 'speak_multilingual'):
        try:
            voice.speak_multilingual(text)
        except Exception as e:
            logger.error(f"Voice speak error: {e}")
            print(f"Jarvis: {text}")
    else:
        print(f"Jarvis: {text}")


def main():
    logger.info("Jarvis starting up...")
    import reminders

    import winsound

    def on_reminder_due(reminder):
        message = f"Reminder: {reminder['task']}"
        # Play an alarm sound - 3 beeps
        for _ in range(3):
            winsound.Beep(1000, 400)  # frequency 1000Hz, duration 400ms
            time.sleep(0.15)
        safe_speak(message) if use_voice else print(f"\nJarvis: {message}")
    reminders.start_background_checker(on_reminder_due)
    print("Jarvis: Systems online.")
    print("Default Mode: TYPE MODE. Type 'zen' to switch to Voice Mode, or 'exit' to quit.")

    use_voice = False

    while True:
        try:
            if not use_voice:
                command = get_command()
                if not command:
                    continue

                if command in ["exit", "quit", "bye"]:
                    print("Jarvis: Goodbye!")
                    break

                if "zen" in command:
                    use_voice = True
                    safe_speak("Voice mode activated. Say 'type mode' to return to typing.")
                    remaining = command.replace("zen", "", 1).strip()
                    if remaining:
                        reply = respond(remaining)
                        if reply:
                            safe_speak(reply)
                    continue

                reply = respond(command)
                if reply is None:
                    print("Jarvis: Goodbye!")
                    break
                print(f"Jarvis: {reply}")

            else:
                heard = ""
                if voice and hasattr(voice, 'listen'):
                    heard = voice.listen(timeout=10)
                else:
                    print("Jarvis: Voice module unavailable. Returning to type mode.")
                    use_voice = False
                    continue

                if not heard:
                    # Continue listening in voice mode on timeout without dropping out
                    continue

                if any(k in heard for k in ["type mode", "exit voice", "stop zen"]):
                    use_voice = False
                    safe_speak("Switching back to type mode.")
                    continue

                if heard in ["exit", "quit", "exit program", "bye"]:
                    safe_speak("Goodbye!")
                    break

                reply = respond(heard)
                if reply is None:
                    safe_speak("Goodbye!")
                    break
                
                # Speak back every sentence aloud in voice mode
                safe_speak(reply)


        except (KeyboardInterrupt, EOFError):
            print("\nJarvis: Goodbye!")
            logger.info("Jarvis exited cleanly by user.")
            break
        except Exception as e:
            logger.error(f"Unhandled error in main execution loop: {e}", exc_info=True)
            print(f"\nJarvis: Recovery active — encountered an error ({e}). Continuing smoothly...")
            use_voice = False


if __name__ == "__main__":
    main()
