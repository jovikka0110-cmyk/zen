import os
import sys
import io
import warnings
import logging
import json
import socket
from dotenv import load_dotenv
from google import genai

# Suppress SDK warnings
warnings.filterwarnings("ignore")
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)

script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)

MEMORY_FILE = os.path.join(script_dir, 'memory.json')
LOG_FILE = os.path.join(script_dir, 'jarvis.log')

# Setup dedicated logging for error tracking
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger("JarvisBrain")

API_KEY = os.getenv('GEMINI_API_KEY')

client = None
if API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        client = None

MODELS_TO_TRY = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
]
SYSTEM_INSTRUCTION = (
    "You are Zen, a helpful AI assistant. Always reply in the SAME language "
    "the user just wrote in — if they write in Tamil (Tamil script), reply "
    "fully in Tamil. If they write in English, reply in English. Never mix "
    "languages within a single reply unless explicitly asked to.\n\n"
    "REMINDERS & ALARMS: You have full built-in support for reminders and alarms. "
    "When a user asks to set a reminder or alarm, confirm that the system will alert them with browser beeps and voice notifications.\n\n"
    "STRICT ACCESS POLICY: Social media websites (such as Instagram, Facebook, Twitter, TikTok, "
    "Reddit, Snapchat, LinkedIn, Pinterest, Tumblr) are strictly DENIED and blocked. Access is "
    "ONLY permitted to educational and resource websites (such as Google, GitHub, Wikipedia, "
    "Khan Academy, Coursera, StackOverflow, GeeksforGeeks, W3Schools, arXiv, ChatGPT, Udemy, edX). "
    "If the user asks to access or open social media, decline politely and state that social media access is denied."
)

TUTOR_SYSTEM_INSTRUCTION = (
    "You are Jarvis, a friendly, patient, interactive programming tutor. "
    "Your mission is to teach programming languages (Python, JavaScript, HTML/CSS, C++, Java, SQL, etc.) "
    "with continuous HANDS-ON experience.\n\n"
    "TUTOR RULES:\n"
    "1. Be encouraging, warm, and supportive like a personal coding mentor.\n"
    "2. Always reply in the SAME language the user wrote in (Tamil or English).\n"
    "3. Keep theoretical explanations concise. ALWAYS include a small HANDS-ON coding challenge or code exercise for the user after explaining.\n"
    "4. When the user posts code or an answer, review it carefully, applaud their success, gently explain any fixes needed, and present the next hands-on step.\n"
    "5. Use clear code blocks (`...`) for code snippets and format your response with clean markdown headers and bullet points.\n"
    "6. Social media access is strictly blocked."
)


class suppress_stderr:
    """Context manager to silence SDK warning prints to stderr."""
    def __enter__(self):
        self._old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self._old_stderr


def is_online(host="8.8.8.8", port=53, timeout=1.5):
    """Check if internet connection is available quickly and reliably."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def load_memory():
    """Load JSON memory file or return default structure if missing/corrupted."""
    if not os.path.exists(MEMORY_FILE):
        return {"saved_facts": [], "chat_history": [], "tutor_mode": False, "tutor_topic": ""}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"saved_facts": [], "chat_history": data, "tutor_mode": False, "tutor_topic": ""}
            if isinstance(data, dict):
                data.setdefault("saved_facts", [])
                data.setdefault("chat_history", [])
                data.setdefault("tutor_mode", False)
                data.setdefault("tutor_topic", "")
                return data
            return {"saved_facts": [], "chat_history": [], "tutor_mode": False, "tutor_topic": ""}
    except Exception as e:
        logger.warning(f"Memory file read/parse error (recovering defaults): {e}")
        return {"saved_facts": [], "chat_history": [], "tutor_mode": False, "tutor_topic": ""}


def save_memory(data):
    """Save memory dict to memory.json safely."""
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")


def set_tutor_mode(active=True, topic=""):
    """Set tutor mode status and current programming topic in memory.json safely."""
    try:
        memory = load_memory()
        memory["tutor_mode"] = bool(active)
        if topic:
            memory["tutor_topic"] = str(topic)
        save_memory(memory)
        return memory["tutor_mode"]
    except Exception as e:
        logger.error(f"Error setting tutor mode: {e}")
        return False


def get_tutor_mode():
    """Retrieve tutor mode status and active topic from memory.json safely."""
    try:
        memory = load_memory()
        return memory.get("tutor_mode", False), memory.get("tutor_topic", "")
    except Exception as e:
        logger.error(f"Error getting tutor mode: {e}")
        return False, ""


def add_fact(fact):
    """Add a remembered fact into memory.json safely."""
    try:
        memory = load_memory()
        if fact and fact not in memory["saved_facts"]:
            memory["saved_facts"].append(fact)
            save_memory(memory)
    except Exception as e:
        logger.error(f"Error adding fact to memory: {e}")


def get_facts():
    """Retrieve saved facts from memory.json safely."""
    try:
        memory = load_memory()
        return memory.get("saved_facts", [])
    except Exception as e:
        logger.error(f"Error retrieving facts: {e}")
        return []


def extract_response_text(response):
    """Safely extract text from candidate parts to avoid non-text/thought_signature warnings."""
    if not response:
        return ""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            if hasattr(response, 'candidates') and response.candidates:
                parts = response.candidates[0].content.parts
                text_parts = []
                for p in parts:
                    if getattr(p, 'thought', False):
                        continue
                    if hasattr(p, 'text') and p.text:
                        text_parts.append(str(p.text))
                if text_parts:
                    return "".join(text_parts).strip()
        except Exception as e:
            logger.debug(f"Candidate text extraction error: {e}")

        try:
            return getattr(response, 'text', '') or ""
        except Exception as e:
            logger.debug(f"Direct text attribute extraction error: {e}")
            return ""


def get_offline_response(user_input):
    """Generate an intelligent offline response using saved facts and local intent handling."""
    try:
        memory = load_memory()
        saved_facts = memory.get("saved_facts", [])
        user_lower = user_input.lower().strip()

        # Check for matches in saved memory facts
        words = [w for w in user_lower.split() if len(w) > 3]
        if words and saved_facts:
            matching_facts = [f for f in saved_facts if any(w in f.lower() for w in words)]
            if matching_facts:
                return (
                    "[Offline Mode] I found relevant saved facts in memory:\n" +
                    "\n".join(f"- {f}" for f in matching_facts)
                )

        if any(k in user_lower for k in ["fact", "remember", "memory"]):
            if saved_facts:
                return "[Offline Mode] Saved facts in memory:\n" + "\n".join(f"- {f}" for f in saved_facts)
            else:
                return "[Offline Mode] No saved facts found in memory."

        if any(k in user_lower for k in ["who are you", "what are you", "your name"]):
            return "[Offline Mode] I am Jarvis, your personal AI assistant. (Running in Offline Mode)"

        if any(k in user_lower for k in ["what can you do", "help", "commands"]):
            return (
                "[Offline Mode] Disconnected from Gemini AI. Available offline commands:\n"
                "- Calculations: e.g. 'calculate 45 * 12'\n"
                "- Time: 'what time is it'\n"
                "- Notes: 'save note ...' or 'my notes'\n"
                "- Open Sites: 'open google', 'open youtube'"
            )

        return (
            "[Offline Mode] Currently offline or cannot connect to Gemini AI. "
            "Local commands like 'time', 'calculate', 'note', and 'my notes' are fully working!"
        )
    except Exception as e:
        logger.error(f"Error generating offline response: {e}")
        return "[Offline Mode] System operational in offline mode."


def think(user_input, file_data=None):
    """Send user_input and optional file_data (image/doc) to Gemini with memory context."""
    global client

    # Check internet availability first
    online = is_online()

    if not online:
        logger.info("Internet connection unavailable. Routing query to offline fallback engine.")
        reply = get_offline_response(user_input)
        save_chat_turn(user_input, reply)
        return reply

    if client is None:
        if API_KEY:
            try:
                client = genai.Client(api_key=API_KEY)
            except Exception as e:
                logger.error(f"Failed to re-initialize Gemini client: {e}")
        if client is None:
            logger.warning("Gemini API client not initialized.")
            reply = get_offline_response(user_input)
            save_chat_turn(user_input, reply)
            return reply

    memory = load_memory()
    chat_history = memory.get("chat_history", [])
    saved_facts = memory.get("saved_facts", [])

    history_lines = []
    for item in chat_history:
        if isinstance(item, dict):
            role = "User" if item.get("role") == "user" else "Zen"
            history_lines.append(f"{role}: {item.get('text', '')}")
        elif isinstance(item, str):
            history_lines.append(item)

    history_lines.append(f"User: {user_input}")

    prompt_parts = []
    if saved_facts:
        facts_summary = "\n".join(f"- {fact}" for fact in saved_facts)
        prompt_parts.append(f"[System Context / User Facts Memory]:\n{facts_summary}")

    recent_history = history_lines[-10:]
    prompt_parts.append("\n".join(recent_history))

    prompt_text = "\n\n".join(prompt_parts)

    from google.genai import types as genai_types

    contents_payload = []
    if file_data and isinstance(file_data, dict):
        raw_bytes = file_data.get("bytes")
        mime_type = file_data.get("mime_type", "image/png")
        filename = file_data.get("filename", "attached_file")

        if raw_bytes and mime_type.startswith("image/"):
            try:
                image_part = genai_types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)
                contents_payload.append(image_part)
                logger.info(f"Attached image {filename} ({mime_type}) to Gemini payload.")
            except Exception as img_err:
                logger.error(f"Error creating Part from image bytes: {img_err}")
        elif raw_bytes:
            try:
                text_content = raw_bytes.decode("utf-8", errors="ignore")
                prompt_text += f"\n\n[Attached File Content: {filename} ({mime_type})]:\n{text_content[:8000]}"
            except Exception as txt_err:
                logger.error(f"Error reading file bytes as text: {txt_err}")

    contents_payload.append(prompt_text)

    reply = None
    last_err_msg = ""

    tutor_active, tutor_topic = get_tutor_mode()
    current_sys_instruction = TUTOR_SYSTEM_INSTRUCTION if tutor_active else SYSTEM_INSTRUCTION

    for model_name in MODELS_TO_TRY:
        try:
            with suppress_stderr():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents_payload,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=current_sys_instruction
                        ),
                    )
                    text_result = extract_response_text(response)
            if text_result:
                reply = text_result
                break
        except Exception as e:
            last_err_msg = str(e)
            logger.warning(f"Model {model_name} failed: {e}")
            continue

    if reply is None:
        logger.error(f"All Gemini models failed. Last error: {last_err_msg}")
        if "429" in last_err_msg or "RESOURCE_EXHAUSTED" in last_err_msg:
            reply = "I'm temporarily rate-limited by the Gemini free quota. Please wait a few seconds and try again."
        else:
            reply = get_offline_response(user_input)

    save_chat_turn(user_input, reply)
    return reply



def save_chat_turn(user_input, reply):
    """Safely append user input and assistant response to chat memory without duplication."""
    try:
        memory = load_memory()
        history = memory.get("chat_history", [])
        history.append({"role": "user", "text": str(user_input).strip()})
        history.append({"role": "model", "text": str(reply).strip()})
        memory["chat_history"] = history[-50:]
        save_memory(memory)
    except Exception as e:
        logger.error(f"Error saving chat turn to memory: {e}")


def reset_memory():
    """Clear conversation history and saved facts in memory.json safely."""
    try:
        save_memory({"saved_facts": [], "chat_history": []})
    except Exception as e:
        logger.error(f"Error resetting memory: {e}")