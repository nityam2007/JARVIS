import speech_recognition as sr
import time
from typing import Optional, Tuple

class SpeechRecognitionManager:
    """
    Handles all speech recognition operations including wake word detection and command listening
    """
    def __init__(self, config):
        """Initialize the SpeechRecognitionManager"""
        self.config = config
        self.recognizer = sr.Recognizer()
        self.manual_sleep = False
        
        # Configure recognition settings with longer timeouts for Indian accent
        rec_settings = config["assistant_settings"]["recognition_settings"]
        self.recognizer.energy_threshold = rec_settings.get("energy_threshold", 3000)
        self.recognizer.dynamic_energy_threshold = rec_settings.get("dynamic_energy_threshold", True)
        self.recognizer.pause_threshold = rec_settings.get("pause_threshold", 1.0)  # Increased
        self.recognizer.phrase_threshold = rec_settings.get("phrase_threshold", 0.5)  # Increased
        self.recognizer.non_speaking_duration = rec_settings.get("non_speaking_duration", 0.8)  # Increased
        
        self.language = "en-IN"  # Set to Indian English
        self.operation_timeout = 30  # Timeout for operations
        self.phrase_time_limit = 15  # Maximum phrase duration
        self.adjustment_duration = 1.0  # Duration for ambient noise adjustment
        
        # Wake word settings
        self.wake_words = [word.lower() for word in config["assistant_settings"]["wake_words"]]

    def adjust_for_ambient_noise(self, source, duration=None):
        """Adjust recognition energy threshold based on ambient noise"""
        if duration is None:
            duration = self.adjustment_duration
            
        try:
            print("\nAdjusting for ambient noise... Please wait...")
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            print(f"Energy threshold set to {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"Error adjusting for ambient noise: {e}")

    def extract_command_from_wake_word(self, text: str) -> Optional[str]:
        """
        Extract command if it follows the wake word
        Example: "computer play music" -> "play music"
        """
        text = text.lower()
        for wake_word in self.wake_words:
            if text.startswith(wake_word):
                command = text[len(wake_word):].strip()
                return command if command else None
        return None

    def detect_wake_word(self) -> Tuple[bool, Optional[str]]:
        """
        Listen for wake word and potential command
        
        Returns:
            Tuple[bool, Optional[str]]: (wake_word_detected, command if any)
        """
        with sr.Microphone() as source:
            try:
                self.adjust_for_ambient_noise(source)
                
                print("\nWaiting for wake word...")
                audio = self.recognizer.listen(
                    source,
                    timeout=None,  # No timeout for wake word detection
                    phrase_time_limit=self.phrase_time_limit
                )
                
                text = self.recognizer.recognize_google(audio, language=self.language)
                text = text.lower()
                print(f"Heard: {text}")
                
                # Check if wake word is present
                wake_word_detected = any(word in text for word in self.wake_words)
                if wake_word_detected:
                    # Check if there's a command after the wake word
                    command = self.extract_command_from_wake_word(text)
                    return True, command
                
                return False, None
                
            except sr.WaitTimeoutError:
                print("No speech detected within timeout period")
                return False, None
            except sr.UnknownValueError:
                print("Could not understand audio")
                return False, None
            except sr.RequestError as e:
                print(f"Could not request results: {e}")
                return False, None
            except Exception as e:
                print(f"Wake word detection error: {e}")
                return False, None

    def listen(self) -> Optional[str]:
        """
        Listen for and recognize speech command
        
        Returns:
            Optional[str]: Recognized text if successful, None otherwise
        """
        with sr.Microphone() as source:
            try:
                self.adjust_for_ambient_noise(source)
                
                print("\nListening...")
                audio = self.recognizer.listen(
                    source,
                    timeout=self.operation_timeout,
                    phrase_time_limit=self.phrase_time_limit
                )
                
                print("Processing speech...")
                text = self.recognizer.recognize_google(audio, language=self.language)
                print(f"Command: {text}")
                return text.lower()
                
            except sr.WaitTimeoutError:
                print("No speech detected within timeout period")
                return None
            except sr.UnknownValueError:
                print("Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"Could not request results: {e}")
                return None
            except Exception as e:
                print(f"Listening error: {e}")
                return None

    def toggle_manual_sleep(self):
        """Toggle manual sleep mode"""
        self.manual_sleep = not self.manual_sleep
        return self.manual_sleep