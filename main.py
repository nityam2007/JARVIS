#!/usr/bin/env python3
"""
Voice Assistant Main Module
Integrates all components to create a complete voice assistant system
"""
# Add this to your imports at the top of main.py
from typing import Tuple, Optional, List  # Add this line

# Your existing imports
import os
import json
import sys
import time
import random
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import warnings
import threading
import queue

# Import custom modules
from modules.audio import AudioManager
from modules.speech import SpeechRecognitionManager
from modules.system import SystemController
from modules.memory import MemoryManager
from modules.spotify_controller import SpotifyController

# Suppress warnings
warnings.filterwarnings("ignore")

class Assistant:
    """
    Main Assistant class that integrates all components and manages the voice assistant's operation
    """
    def __init__(self):
        """Initialize the assistant and all its components"""
        # Create necessary directories
        self._create_directories()
        
        # Initialize components
        self.load_config()
        self.setup_ai()
        
        self.audio = AudioManager(self.config)
        self.speech = SpeechRecognitionManager(self.config)
        
        # Initialize Spotify first
        spotify_path = self.config["applications"]["media"].get("spotify")
        self.spotify = SpotifyController(spotify_path) if spotify_path else None
        
        # Initialize system controller only once
        self.system = SystemController(self.config)
        self.memory = MemoryManager(self.config)
        
        # State variables
        self.is_listening = True
        self.is_active = False
        self.is_processing = False
        self.last_activity = time.time()
        self.command_queue = queue.Queue()
        
        # Start background threads
        self._start_idle_checker()
        self._start_command_processor()

    def _create_directories(self):
        """Create necessary directories for the assistant"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        #os.makedirs(os.path.join(base_dir, 'audio_cache'), exist_ok=True)
        os.makedirs(os.path.join(base_dir, 'audio_temp'), exist_ok=True)

    def load_config(self):
        """Load configuration from config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)

    def setup_ai(self):
        """Setup AI client and load environment variables"""
        try:
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
            load_dotenv(env_path)
            
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables")
                
            self.ai_client = Groq(api_key=api_key)
        except Exception as e:
            print(f"Error setting up AI client: {e}")
            sys.exit(1)

    def _start_idle_checker(self):
        """Start the idle checking thread"""
        self.idle_checker = threading.Thread(target=self._check_idle, daemon=True)
        self.idle_checker.start()

    def _start_command_processor(self):
        """Start the command processing thread"""
        self.command_processor = threading.Thread(target=self._process_command_queue, daemon=True)
        self.command_processor.start()

    def _check_idle(self):
        """Check for idle timeout"""
        while self.is_listening:
            if self.is_active and not self.speech.manual_sleep:
                timeout = self.config["assistant_settings"]["voice_settings"]["timeout_seconds"]
                if time.time() - self.last_activity > timeout:
                    print("Going to sleep due to inactivity...")
                    self.deactivate()
            time.sleep(1)

    def _process_command_queue(self):
        """Process commands from the queue"""
        while self.is_listening:
            try:
                if not self.command_queue.empty():
                    command = self.command_queue.get()
                    self.is_processing = True
                    self.process_command(command)
                    self.is_processing = False
                    self.command_queue.task_done()
                time.sleep(0.1)
            except Exception as e:
                print(f"Error processing command: {e}")
                self.is_processing = False

    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS output"""
        # Remove special characters and formatting
        replacements = {
            "*": "",
            "#": "",
            "**": "",
            "__": "",
            "`": "",
            "```": "",
            "\n": ". ",  # Replace newlines with pause
            "...": ". ",  # Replace ellipsis with pause
            "Jarvis's music module is online": "",
            "Requesting song": "",
            "Playing:": "Now playing",
            "Error:": "Sorry,",
            "Error": "Sorry,"
        }
        
        cleaned_text = text
        for old, new in replacements.items():
            cleaned_text = cleaned_text.replace(old, new)
        
        # Remove multiple spaces
        cleaned_text = " ".join(cleaned_text.split())
        
        # Remove any remaining special characters
        cleaned_text = ''.join(char for char in cleaned_text 
                             if char.isalnum() or char in ' .,!?-:()')
        
        return cleaned_text.strip()

    def get_response(self, response_type):
        """Get a random response from configured responses"""
        responses = self.config["responses"].get(response_type, [])
        return random.choice(responses) if responses else None

    def get_ai_response(self, text):
        """Get AI response for user input"""
        try:
            # Add user message to memory
            self.memory.add_to_history("user", text)

            # Get acknowledgment
            ack = self.get_response("acknowledgments")
            if ack:
                self.audio.speak(self._clean_text_for_tts(ack), priority=True)

            # Get conversation history for context
            messages = [
                {"role": "system", "content": self.config["ai_settings"]["system_prompt"]},
                *self.memory.get_messages_for_ai()
            ]

            # Generate AI response
            completion = self.ai_client.chat.completions.create(
                model=self.config["ai_settings"]["model"],
                messages=messages,
                temperature=self.config["ai_settings"]["temperature"],
                max_tokens=self.config["ai_settings"]["max_tokens"],
                stream=True
            )

            response = "".join(chunk.choices[0].delta.content or "" 
                             for chunk in completion)

            # Add assistant response to memory
            self.memory.add_to_history("assistant", response)
            return self._clean_text_for_tts(response)

        except Exception as e:
            print(f"AI error: {e}")
            error_msg = self.get_response("errors")
            return self._clean_text_for_tts(error_msg if error_msg else "I encountered an error.")

    def _get_command_variations(self):
        """Get command variations for better recognition"""
        return {
            'mute_commands': [
                # AI speech muting
                "shut up", "stop talking", "be quiet",
                "silence please", "stop speaking", "mute voice",
                "quiet now", "stop ai", "ai mute",
                "stop assistant", "quiet please", "hush"
            ],
            'unmute_commands': [
                # AI speech unmuting
                "speak up", "continue talking", "unmute voice",
                "start speaking", "unmute ai", "ai unmute",
                "resume speaking", "voice on", "assistant speak",
                "you can talk", "resume voice","mute"
            ],
            
            'music_keywords': [
                # Basic music commands
                "play", "music", "song", "track",
                
                # Playlist commands
                "play playlist", "start playlist",
                "shuffle playlist", "play mix",
                
                # Artist commands
                "play artist", "music by",
                
                # Album commands
                "play album", "start album",
                
                # Genre commands
                "play rock", "play jazz", "play pop",
                "play classical", "play hip hop"
            ],
            
            'volume_commands': [
                # Volume up
                "volume up", "louder", "increase volume",
                "turn it up", "raise volume",
                
                # Volume down
                "volume down", "quieter", "decrease volume",
                "turn it down", "lower volume"
            ],
            
            'playback_controls': [
                # Play/Pause
                "play", "pause", "resume", "stop",
                
                # Navigation
                "next", "previous", "skip", "back",
                "next song", "previous song",
                
                # Shuffle/Repeat
                "shuffle", "repeat", "repeat one",
                "shuffle on", "shuffle off",
                
                # Like/Save
                "like song", "save song", "like this",
                "add to favorites"
            ]
        }


    # 1. Update the music command handling section in the handle_music_command method:

    def handle_music_command(self, command: str) -> Tuple[bool, str]:
        """Enhanced music command handler"""
        if not self.spotify:
            return False, "Spotify controller not initialized"

        try:
            command = command.lower()
            success, msg = False, "Unknown command"

            # Launch Spotify
            if "open spotify" in command:
                success, msg = self.spotify.launch_spotify()
                
            # Handle play commands
            elif "play" in command:
                if command in ["play", "play music", "play song", "play something"]:
                    success, msg = self.spotify.play_random_music()
                else:
                    # Extract search term after "play"
                    search_term = command.replace("play", "").strip()
                    
                    # Determine category based on command
                    if "playlist" in search_term:
                        category = "playlists"
                        search_term = search_term.replace("playlist", "").strip()
                    elif "artist" in search_term:
                        category = "artists"
                        search_term = search_term.replace("artist", "").strip()
                    elif "album" in search_term:
                        category = "albums"
                        search_term = search_term.replace("album", "").strip()
                    else:
                        category = "songs"
                    
                    success, msg = self.spotify.search_and_play(search_term, category)

            # Handle playback controls
            elif command in ["pause", "stop"]:
                success, msg = self.spotify.control_playback("pause")
            elif command in ["resume", "continue"]:
                success, msg = self.spotify.control_playback("play")
            elif command in ["next", "skip", "next song"]:
                success, msg = self.spotify.control_playback("next")
            elif command in ["previous", "back", "last song"]:
                success, msg = self.spotify.control_playback("previous")
            #elif command == "mute":
              #  success, msg = self.spotify.toggle_mute()
            elif "shuffle" in command:
                success, msg = self.spotify.control_playback("shuffle")
            elif "repeat" in command:
                success, msg = self.spotify.control_playback("repeat")
            elif "like" in command or "save" in command:
                success, msg = self.spotify.control_playback("like")

            # Handle volume
            elif "volume up" in command or "louder" in command:
                success, msg = self.spotify.adjust_volume("up", 2)
            elif "volume down" in command or "quieter" in command:
                success, msg = self.spotify.adjust_volume("down", 2)

            # Window controls
            elif "minimize" in command:
                success, msg = self.spotify.minimize_window()
            elif "restore" in command:
                success, msg = self.spotify.restore_window()
            elif "close" in command:
                success, msg = self.spotify.close_spotify()

            return success, msg

        except Exception as e:
            print(f"Error in music command handler: {e}")
            return False, f"Error processing music command: {e}"


    def process_command(self, command):
        """Process user command"""
        if not command:
            return

        command = command.lower().strip()
        variations = self._get_command_variations()
        
        # Music commands - Handle these before AI
        if command == "open spotify" or any(keyword in command for keyword in variations['music_keywords']):
            try:
                if self.spotify:
                    print(f"Processing music command: {command}")  # Debug output
                    success, msg = self.handle_music_command(command)
                    
                    if success is not None and msg is not None:
                        msg = self._clean_text_for_tts(msg)
                        self.audio.speak(msg)
                        if "play" in command or "pause" in command:
                            time.sleep(1)  # Give time for playback to start/stop
                        self.audio.wait_until_done()
                    return
                else:
                    self.audio.speak("Spotify controller is not initialized")
                    return
            except Exception as e:
                print(f"Error processing music command: {e}")
                self.audio.speak("There was an error with the music command")
                return

        # Volume control
        if any(cmd in command for cmd in variations['volume_commands']):
            try:
                if self.spotify:
                    success, msg = self.handle_music_command(command)
                    if success is not None and msg is not None:
                        msg = self._clean_text_for_tts(msg)
                        self.audio.speak(msg)
                        self.audio.wait_until_done()
                    return
            except Exception as e:
                print(f"Error adjusting volume: {e}")
                return

        # Playback control
        if any(cmd in command for cmd in variations['playback_controls']):
            try:
                if self.spotify:
                    success, msg = self.handle_music_command(command)
                    if success is not None and msg is not None:
                        msg = self._clean_text_for_tts(msg)
                        self.audio.speak(msg)
                        if "play" in command or "pause" in command:
                            time.sleep(1)  # Give time for playback to start/stop
                        self.audio.wait_until_done()
                    return
            except Exception as e:
                print(f"Error controlling playback: {e}")
                return
        
        # Handle sleep/deactivation commands
        if any(phrase in command for phrase in [
            "go to sleep", "sleep now", "sleep mode", 
            "stop listening", "you can sleep"
        ]):
            self.deactivate(reason="user_requested")
            return

        # Voice control commands get immediate priority
        if any(cmd in command for cmd in variations['mute_commands']):
            # Stop any ongoing AI speech
            self.audio.stop()
            self.audio.toggle_mute()
            print("AI voice muted")
            return
            
        elif any(cmd in command for cmd in variations['unmute_commands']):
            self.audio.unmute()
            print("AI voice unmuted")
            return

        

        # Application control with variations
        if any(cmd in command for cmd in ["open", "start", "launch", "run"]):
            target = command
            for cmd in ["open", "start", "launch", "run"]:
                target = target.replace(cmd, "").strip()
            
            if "and write" in target:
                parts = target.split("and write", 1)
                app_name = parts[0].strip()
                text_to_write = parts[1].strip()
                success, msg = self.system.open_application(app_name, text_to_write)
            else:
                success, msg = self.system.open_website(target)
                if not success:
                    success, msg = self.system.open_application(target)
            
            self.audio.speak(self._clean_text_for_tts(msg))
            self.audio.wait_until_done()
            return

        # Writing commands
        if command.startswith("write"):
            text = command.replace("write", "", 1).strip()
            success, msg = self.system.write_to_current_app(text)
            self.audio.speak(self._clean_text_for_tts(msg))
            self.audio.wait_until_done()
            return

        # Close/Exit variations
        if any(cmd in command for cmd in ["close", "exit", "quit", "terminate", "stop"]):
            target = command
            for cmd in ["close", "exit", "quit", "terminate", "stop"]:
                target = target.replace(cmd, "").strip()
            
            if any(word in target for word in ["spotify", "music", "song", "player"]):
                success, msg = self.system.handle_music_command("close")
            else:
                success, msg = self.system.close_application(target)
            
            self.audio.speak(self._clean_text_for_tts(msg))
            self.audio.wait_until_done()
            return

        # Window control with variations
        if any(cmd in command for cmd in ["minimize", "hide", "shrink"]):
            target = command.replace("minimize", "").replace("hide", "").replace("shrink", "").strip()
            success, msg = self.system.minimize_window(target)
            self.audio.speak(self._clean_text_for_tts(msg))
            self.audio.wait_until_done()
            return

        if any(cmd in command for cmd in ["maximize", "expand", "full screen"]):
            target = command.replace("maximize", "").replace("expand", "").replace("full screen", "").strip()
            success, msg = self.system.maximize_window(target)
            self.audio.speak(self._clean_text_for_tts(msg))
            self.audio.wait_until_done()
            return

        # System commands with variations
        if any(cmd in command for cmd in ["shutdown", "restart", "sleep", "hibernate", "power off", "reboot"]):
            for cmd, msg in self.config["system_commands"].items():
                if any(keyword in command for keyword in [cmd, f"{cmd} computer", f"{cmd} system"]):
                    success, msg = self.system.execute_system_command(msg)
                    self.audio.speak(f"Executing {cmd} command")
                    self.audio.wait_until_done()
                    return

        # Exit assistant command variations
        if any(word in command for word in ["goodbye", "bye", "see you", "later", "good night"]):
            self.cleanup()
            return

        # Default to AI conversation for unhandled commands
        response = self.get_ai_response(command)
        self.audio.speak(response)
        return
        self.audio.wait_until_done()
        
        
    def activate(self):
        """Activate the assistant with enhanced feedback"""
        self.is_active = True
        self.last_activity = time.time()
        
        # Simple, clear greetings without special characters
        greetings = [
            "How can I help?",
            "Ready to assist you",
            "What can I do for you?",
            "Yes, I'm here",
            "I'm listening",
            "How may I assist?",
            "At your service",
            "Ready for your command",
            # Additional natural responses
            "What do you need?",
            "I'm all ears",
            "Tell me what you need",
            "How can I be of help?"
        ]
        
        greeting = random.choice(greetings)
        self.audio.speak(self._clean_text_for_tts(greeting))
        self.audio.wait_until_done()
        print("\nAssistant activated and ready for commands")

    def deactivate(self, reason="timeout"):
        """
        Deactivate the assistant with context-aware feedback
        
        Args:
            reason (str): Reason for deactivation 
                ("timeout", "max_commands", "manual", "error", "user_requested")
        """
        if self.is_active:
            # Only speak a message for user-requested deactivation
            if reason == "user_requested":
                messages = [
                    "Going offline",
                    "As you wish",
                    "Until next time",
                    "Standing by"
                ]
                msg = random.choice(messages)
                self.audio.speak(self._clean_text_for_tts(msg))
                self.audio.wait_until_done()
            
            self.is_active = False
            print("\nAssistant inactive")
            time.sleep(0.5)

    def cleanup(self):
        """Cleanup and exit with enhanced feedback"""
        print("\nCleaning up...")
        self.is_listening = False
        
        cleanup_messages = [
            "Shutting down now. Goodbye!",
            "All systems shutting down. See you later!",
            "Goodbye! Have a great day!",
            "Powering down. Thanks for using me!",
            "Shutting down systems. Farewell!"
        ]
        
        goodbye = random.choice(cleanup_messages)
        self.audio.speak(self._clean_text_for_tts(goodbye))
        self.audio.wait_until_done()
        time.sleep(1)
        self.audio.stop()
        sys.exit(0)

    def run(self):
        """Main run loop with minimal interruptions"""
        print(f"\nStarting {self.config['assistant_settings']['name']}...")
        welcome_msg = f"System ready. Wake word is {self.config['assistant_settings']['name']}"
        self.audio.speak(self._clean_text_for_tts(welcome_msg))
        self.audio.wait_until_done()
        
        consecutive_failures = 0
        max_failures = 3
        command_timeout = 20
        
        
        while self.is_listening:
            try:
                # Wait for wake word when inactive
                if not self.is_active:
                    print("\nWaiting for wake word...")
                    wake_word_detected, initial_command = self.speech.detect_wake_word()
                    
                    if wake_word_detected:
                        consecutive_failures = 0  # Reset failure counter
                        self.activate()
                        
                        # Process initial command if present (combined wake word + command)
                        if initial_command:
                            print(f"Processing initial command: {initial_command}")
                            self.process_command(initial_command)
                            #self.audio.wait_until_done()
                            command_count = 1
                        else:
                            command_count = 0
                            
                        # Start command session
                        command_start_time = time.time()
                        max_commands = 3  # Number of commands before requiring wake word again
                        
                        # Continue listening for more commands
                        while self.is_active and command_count < max_commands:
                            # Check for timeout
                            if time.time() - command_start_time > command_timeout:
                                print("\nCommand timeout reached, going to sleep...")
                                self.deactivate()
                                break

                            # Listen for next command
                            if command_count > 0:  # Only prompt if not first command
                                print("\nListening for next command...")
                            command = self.speech.listen()
                            
                            if command:
                                # Reset timeout on successful command
                                command_start_time = time.time()
                                command_count += 1
                                self.last_activity = time.time()
                                
                                # Process the command
                                self.process_command(command)
                                
                                # Wait for any ongoing speech to complete
                                #
                                # self.audio.wait_until_done()
                                
                                # If this was the last allowed command, go to sleep
                                if command_count >= max_commands:
                                    print("\nMaximum commands reached, going to sleep...")
                                    #self.audio.speak(self._clean_text_for_tts(
                                    #    "Maximum commands reached. Wake me when you need me again."))
                                    #self.audio.wait_until_done()
                                    self.deactivate()
                            else:
                                consecutive_failures += 1
                                if consecutive_failures >= max_failures:
                                    print("\nToo many failed attempts, going to sleep...")
                                    #self.audio.speak(self._clean_text_for_tts(
                                    #    "I'm having trouble understanding. I'll go to sleep for now."))
                                    #self.audio.wait_until_done()
                                    self.deactivate()
                                    consecutive_failures = 0  # Reset counter
                                    break
                                
                time.sleep(0.1)  # Small delay to prevent CPU overuse
                
            except KeyboardInterrupt:
                self.cleanup()
            except Exception as e:
                print(f"\nError in main loop: {e}")
                time.sleep(1)

def main():
    """Entry point of the application"""
    try:
        assistant = Assistant()
        assistant.run()
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()