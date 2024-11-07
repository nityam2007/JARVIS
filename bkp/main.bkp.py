import os
import speech_recognition as sr
from gtts import gTTS
import pygame
import tempfile
import subprocess
import threading
from queue import Queue
from datetime import datetime
import webbrowser
import sys
import time
import uuid
import json
import random
from groq import Groq
from dotenv import load_dotenv
import warnings
import pyautogui
import keyboard

warnings.filterwarnings("ignore")
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class AudioManager:
    def __init__(self, config):
        pygame.mixer.init()
        self.speech_queue = Queue()
        self.is_speaking = False
        self.is_muted = False
        self.should_stop = False
        self.temp_dir = tempfile.mkdtemp()
        self.volume = config["assistant_settings"]["voice_settings"]["volume"]
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()

    def _process_speech_queue(self):
        while not self.should_stop:
            try:
                if not self.speech_queue.empty() and not self.should_stop and not self.is_muted:
                    text, priority = self.speech_queue.get()
                    if text:
                        self._speak_text(text)
                    self.speech_queue.task_done()
                time.sleep(0.1)
            except Exception as e:
                print(f"Speech error: {e}")
                time.sleep(0.1)

    def _speak_text(self, text):
        try:
            if self.should_stop or self.is_muted:
                return
                
            self.is_speaking = True
            temp_file = os.path.join(self.temp_dir, f'speech_{uuid.uuid4()}.mp3')
            
            # Split long text into sentences for better speech
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            
            for sentence in sentences:
                if self.should_stop or self.is_muted:
                    break
                    
                tts = gTTS(text=sentence, lang='en', tld='co.in')
                tts.save(temp_file)
                
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy() and not self.should_stop and not self.is_muted:
                    pygame.time.Clock().tick(10)
                
                try:
                    os.remove(temp_file)
                except:
                    pass
                    
            self.is_speaking = False
            
        except Exception as e:
            print(f"Speech error: {e}")
            self.is_speaking = False

    def speak(self, text, priority=False):
        if text and not self.should_stop and not self.is_muted:
            self.speech_queue.put((text, priority))

    def wait_until_done(self):
        """Wait until all speech is complete"""
        while self.is_speaking or not self.speech_queue.empty():
            time.sleep(0.1)

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.stop()
            self.speech_queue.queue.clear()
        return self.is_muted

    def unmute(self):
        self.is_muted = False
        self.speak("Voice output restored")

    def stop(self):
        self.should_stop = True
        pygame.mixer.music.stop()
        self.speech_queue.queue.clear()
        pygame.mixer.quit()

class SystemController:
    def __init__(self, config):
        self.config = config
        self.apps = config["applications"]
        self.urls = config["urls"]
        self.hotkeys = config["hotkeys"]
        self.register_hotkeys()

    def register_hotkeys(self):
        """Register system-wide hotkeys"""
        try:
            keyboard.add_hotkey('ctrl+w', lambda: keyboard.send('alt+f4'))
            keyboard.add_hotkey('alt+tab', lambda: keyboard.send('alt+tab'))
            keyboard.add_hotkey('win+d', lambda: keyboard.send('win+d'))
            
            # Media controls
            spotify_keys = {
                "play_pause": "space",
                "next_track": "ctrl+right",
                "previous_track": "ctrl+left",
                "volume_up": "ctrl+up",
                "volume_down": "ctrl+down"
            }
            
            for action, hotkey in spotify_keys.items():
                try:
                    keyboard.add_hotkey(hotkey, lambda a=action: self.control_spotify(a))
                except Exception as e:
                    print(f"Warning: Could not register hotkey {hotkey}")
                    
        except Exception as e:
            print(f"Warning: Some hotkeys could not be registered")

    def open_application(self, app_name):
        app_name = app_name.lower()
        for category in self.apps.values():
            if app_name in category:
                try:
                    subprocess.Popen(category[app_name])
                    return True, f"Opening {app_name}"
                except Exception as e:
                    return False, f"Error opening {app_name}: {e}"
        return False, f"Application {app_name} not found"

    def open_website(self, site_name):
        site_name = site_name.lower()
        if site_name in self.urls:
            try:
                webbrowser.open(self.urls[site_name])
                return True, f"Opening {site_name}"
            except Exception as e:
                return False, f"Error opening {site_name}: {e}"
        return False, f"Website {site_name} not configured"

    def write_text(self, text):
        try:
            subprocess.Popen(['notepad.exe'])
            time.sleep(1)
            pyautogui.write(text)
            return True, "Text written to Notepad"
        except Exception as e:
            return False, f"Error writing text: {e}"

    def control_spotify(self, command):
        try:
            if command in self.hotkeys["spotify"]:
                keyboard.press_and_release(self.hotkeys["spotify"][command])
                return True, f"Spotify {command} executed"
            return False, "Unknown Spotify command"
        except Exception as e:
            return False, f"Error controlling Spotify: {e}"

class Assistant:
    def __init__(self):
        self.load_config()
        self.audio = AudioManager(self.config)
        self.system = SystemController(self.config)
        self.recognizer = sr.Recognizer()
        self.is_listening = True
        self.is_active = False
        self.last_activity = time.time()
        self.conversation_history = []
        
        # Configure recognition
        rec_settings = self.config["assistant_settings"]["recognition_settings"]
        self.recognizer.energy_threshold = rec_settings["energy_threshold"]
        self.recognizer.dynamic_energy_threshold = rec_settings["dynamic_energy_threshold"]
        self.recognizer.pause_threshold = rec_settings["pause_threshold"]
        self.recognizer.phrase_threshold = rec_settings["phrase_threshold"]
        self.recognizer.non_speaking_duration = rec_settings["non_speaking_duration"]
        
        # Start idle checker
        self.idle_checker = threading.Thread(target=self._check_idle, daemon=True)
        self.idle_checker.start()

    def load_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    def _check_idle(self):
        while self.is_listening:
            if self.is_active:
                timeout = self.config["assistant_settings"]["voice_settings"]["timeout_seconds"]
                if time.time() - self.last_activity > timeout:
                    print("Going to sleep due to inactivity...")
                    self.deactivate()
            time.sleep(1)

    def get_response(self, response_type):
        responses = self.config["responses"].get(response_type, [])
        return random.choice(responses) if responses else None

    def detect_wake_word(self):
        with sr.Microphone() as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                print("\nWaiting for wake word...")
                audio = self.recognizer.listen(source, timeout=30, phrase_time_limit=15)
                text = self.recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")
                
                if any(word in text for word in self.config["assistant_settings"]["wake_words"]):
                    return True
                return False
            except:
                return False

    def listen(self):
        with sr.Microphone() as source:
            try:
                print("\nListening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=100, phrase_time_limit=30)
                text = self.recognizer.recognize_google(audio).lower()
                print(f"Command: {text}")
                self.last_activity = time.time()
                return text
            except sr.UnknownValueError:
                return None
            except sr.RequestError:
                print("Network error in speech recognition")
                return None
            except Exception as e:
                print(f"Listening error: {e}")
                return None

    def get_ai_response(self, text):
        try:
            # Maintain conversation history
            self.conversation_history.append({"role": "user", "content": text})
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-5:]

            # Get acknowledgment
            ack = self.get_response("acknowledgments")
            if ack:
                self.audio.speak(ack, priority=True)
                self.audio.wait_until_done()

            completion = client.chat.completions.create(
                model=self.config["ai_settings"]["model"],
                messages=[
                    {"role": "system", "content": self.config["ai_settings"]["system_prompt"]},
                    *self.conversation_history
                ],
                temperature=self.config["ai_settings"]["temperature"],
                max_tokens=self.config["ai_settings"]["max_tokens"],
                stream=True
            )

            response = "".join(chunk.choices[0].delta.content or "" for chunk in completion)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response

        except Exception as e:
            print(f"AI error: {e}")
            error_msg = self.get_response("errors")
            return error_msg if error_msg else "I encountered an error."

    def process_command(self, command):
        if not command:
            return

        # Voice control commands
        if any(word in command for word in ["mute", "shut up", "be quiet"]):
            is_muted = self.audio.toggle_mute()
            response = self.get_response("mute" if is_muted else "unmute")
            print(response)
            if not is_muted:
                self.audio.speak(response)
                self.audio.wait_until_done()
            return
            
        elif "unmute" in command or "speak up" in command:
            self.audio.unmute()
            return

        # Time query
        if "time" in command:
            current_time = datetime.now().strftime('%I:%M %p')
            response = f"It's {current_time}"
            self.audio.speak(response)
            self.audio.wait_until_done()
            return

        # Application and website commands
        if "open" in command:
            target = command.replace("open", "").strip()
            
            success, msg = self.system.open_website(target)
            if success:
                self.audio.speak(msg)
                self.audio.wait_until_done()
                return
                
            success, msg = self.system.open_application(target)
            self.audio.speak(msg)
            self.audio.wait_until_done()
            return

        # Music controls
        if any(x in command for x in ["play music", "play song", "next song", "previous song"]):
            action = "play_pause"
            if "next" in command: action = "next_track"
            if "previous" in command: action = "previous_track"
            
            success, msg = self.system.control_spotify(action)
            self.audio.speak(msg)
            self.audio.wait_until_done()
            return

        # Exit command
        if "exit" in command or "goodbye" in command:
            self.cleanup()
            return

        # Default to AI conversation
        response = self.get_ai_response(command)
        self.audio.speak(response)
        self.audio.wait_until_done()

    def activate(self):
        self.is_active = True
        self.last_activity = time.time()
        greeting = self.get_response("greetings")
        self.audio.speak(greeting)
        self.audio.wait_until_done()

    def deactivate(self):
        if self.is_active:
            goodbye = self.get_response("goodbyes")
            self.audio.speak(goodbye)
            self.audio.wait_until_done()
            self.is_active = False

    def cleanup(self):
        print("\nCleaning up...")
        goodbye = self.get_response("goodbyes")
        self.audio.speak(goodbye)
        self.audio.wait_until_done()
        time.sleep(1)
        self.audio.stop()
        sys.exit(0)

    def run(self):
        print(f"Starting {self.config['assistant_settings']['name']}...")
        welcome_msg = f"Voice assistant ready. Wake me by saying {self.config['assistant_settings']['name']}"
        self.audio.speak(welcome_msg)
        self.audio.wait_until_done()
        
        while self.is_listening:
            try:
                if not self.is_active:
                    if self.detect_wake_word():
                        self.activate()
                else:
                    command = self.listen()
                    if command:
                        self.process_command(command)
            except KeyboardInterrupt:
                self.cleanup()
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    try:
        assistant = Assistant()
        assistant.run()
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)