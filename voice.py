import os
import sys
import logging
from gtts import gTTS
from playsound import playsound
import tempfile


# Safe import for speech_recognition to prevent IDE linter errors and runtime failures
try:
    import speech_recognition as sr
except ImportError:
    sr = None

script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'jarvis.log')
logger = logging.getLogger("JarvisVoice")


def speak(text):
    """Convert text to speech and print output safely on every call."""
    if not text:
        return

    clean_text = str(text).strip()
    print(f"Jarvis: {clean_text}")

    spoken = False

    # Method 1: Windows Direct SAPI5 via win32com (Instant & 100% reliable on Windows)
    if sys.platform.startswith("win"):
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(clean_text)
            spoken = True
        except Exception as e:
            logger.warning(f"Win32Com SAPI5 speech error: {e}")

    # Method 2: pyttsx3 fallback engine
    if not spoken:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 170)
            engine.say(clean_text)
            engine.runAndWait()
            try:
                engine.stop()
            except Exception:
                pass
            spoken = True
        except Exception as e:
            logger.error(f"pyttsx3 speech error: {e}")


def listen(timeout=10, phrase_time_limit=10):
    """Listen for voice input from microphone with robust online/offline error handling."""
    if sr is None:
        logger.warning("speech_recognition library is not available.")
        print("Jarvis: Voice recognition module ('SpeechRecognition') is missing.")
        return ""

    try:
        recognizer = sr.Recognizer()
        try:
            mic = sr.Microphone()
        except Exception as mic_err:
            logger.error(f"Microphone access error: {mic_err}")
            print("Jarvis: Microphone unavailable or not configured.")
            return ""

        with mic as source:
            print("\nListening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("Recognizing...")
            text = recognizer.recognize_google(audio)
            print(f"You (Voice): {text}")
            return text.lower().strip()

    except Exception as e:
        if sr and hasattr(sr, 'WaitTimeoutError') and isinstance(e, sr.WaitTimeoutError):
            return ""
        if sr and hasattr(sr, 'UnknownValueError') and isinstance(e, sr.UnknownValueError):
            print("Jarvis: Could not understand audio.")
            return ""
        if sr and hasattr(sr, 'RequestError') and isinstance(e, sr.RequestError):
            logger.warning(f"Speech recognition service error (offline): {e}")
            speak("Speech recognition requires internet connection.")
            return ""
        if isinstance(e, (OSError, AttributeError)):
            logger.error(f"Audio device hardware error: {e}")
            speak("Audio device error detected.")
            return ""

        logger.error(f"Unexpected voice input error: {e}", exc_info=True)
        return ""
def speak_multilingual(text):
    """
    Speak text aloud, auto-detecting Tamil vs English and using the
    male neural voice engine for both (ta-IN-ValluvarNeural & en-US-ChristopherNeural).
    """
    if not text:
        return

    clean_text = str(text).replace("[Offline Mode]", "").strip()
    is_tamil = any('\u0B80' <= ch <= '\u0BFF' for ch in clean_text)
    
    spoken = False
    try:
        import asyncio
        import edge_tts
        voice = "ta-IN-ValluvarNeural" if is_tamil else "en-US-ChristopherNeural"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name

        async def _synth():
            comm = edge_tts.Communicate(clean_text, voice)
            await comm.save(temp_path)

        asyncio.run(_synth())
        playsound(temp_path)
        try:
            os.remove(temp_path)
        except Exception:
            pass
        spoken = True
    except Exception as e:
        logger.warning(f"Edge-TTS male voice error: {e}")

    if not spoken:
        if is_tamil:
            try:
                tts = gTTS(text=clean_text, lang='ta')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                    temp_path = fp.name
                tts.save(temp_path)
                playsound(temp_path)
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"gTTS fallback error: {e}")
                print(f"Jarvis: {clean_text}")
        else:
            speak(clean_text)


