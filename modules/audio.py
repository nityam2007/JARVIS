import os
import pygame
import threading
from queue import Queue
import uuid
import time
from gtts import gTTS

class AudioManager:
    """
    Handles all audio output operations including text-to-speech conversion and playback
    """
    def __init__(self, config):
        """
        Initialize the AudioManager with given configuration
        
        Args:
            config (dict): Configuration dictionary containing voice settings
        """
        # Initialize pygame mixer with specific settings for better file handling
        pygame.mixer.init(frequency=16000, channels=1)
        self.speech_queue = Queue()
        self.is_speaking = False
        self.is_muted = False
        self.should_stop = False
        self.volume = config["assistant_settings"]["voice_settings"]["volume"]
        
        # Create audio directories in the project folder
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_dir = os.path.join(self.base_dir, 'audio_cache')
        self.temp_dir = os.path.join(self.base_dir, 'audio_temp')
        
        # Ensure directories exist with proper permissions
        self._setup_directories()
        
        self.speech_thread = threading.Thread(target=self._process_speech_queue, daemon=True)
        self.speech_thread.start()
        
        # Keep track of current audio file
        self.current_audio_file = None

    def _setup_directories(self):
        """Setup audio directories with proper permissions"""
        try:
            # Create directories if they don't exist
            #os.makedirs(self.cache_dir, exist_ok=True)
            os.makedirs(self.temp_dir, exist_ok=True)
            
            print(f"Audio directories setup completed:")
            #print(f"Cache dir: {self.cache_dir}")
            print(f"Temp dir: {self.temp_dir}")
            
            # Clean any existing files
            self._cleanup_old_files(initial=True)
        except Exception as e:
            print(f"Error setting up audio directories: {e}")
            raise

    def _cleanup_old_files(self, initial=False):
        """
        Clean up old temporary files
        
        Args:
            initial (bool): Whether this is the initial cleanup
        """
        def try_remove_file(filepath):
            try:
                if os.path.exists(filepath):
                    # Skip current audio file if it's being played
                    if filepath == self.current_audio_file and pygame.mixer.music.get_busy():
                        return
                    pygame.mixer.music.unload()
                    time.sleep(0.1)  # Give a small delay for file handle to be released
                    os.remove(filepath)
            except Exception as e:
                if not initial:  # Only print errors after initialization
                    print(f"Couldn't remove file {filepath}: {e}")

        for directory in [self.temp_dir, self.cache_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    try_remove_file(filepath)

    def _get_temp_filepath(self):
        """Generate a unique temporary file path"""
        return os.path.join(self.temp_dir, f'speech_{uuid.uuid4()}.mp3')

    def _process_speech_queue(self):
        """Process queued speech items in a separate thread"""
        while not self.should_stop:
            try:
                if not self.speech_queue.empty() and not self.should_stop and not self.is_muted:
                    text, priority = self.speech_queue.get()
                    if text:
                        self._speak_text(text)
                    self.speech_queue.task_done()
                time.sleep(0.1)
            except Exception as e:
                print(f"Speech queue error: {e}")
                time.sleep(0.1)

    def _speak_text(self, text):
        """
        Convert text to speech and play it
        
        Args:
            text (str): Text to be converted to speech
        """
        if self.should_stop or self.is_muted:
            return
            
        self.is_speaking = True
        
        try:
            # Split text into sentences
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            
            for sentence in sentences:
                if self.should_stop or self.is_muted:
                    break
                
                # Generate new temp file path
                self.current_audio_file = self._get_temp_filepath()
                
                # Create and save audio file
                tts = gTTS(text=sentence, lang='en', tld='co.in')
                tts.save(self.current_audio_file)
                
                # Play the audio
                try:
                    pygame.mixer.music.load(self.current_audio_file)
                    pygame.mixer.music.set_volume(self.volume)
                    pygame.mixer.music.play()
                    
                    # Wait for audio to complete
                    while pygame.mixer.music.get_busy() and not self.should_stop and not self.is_muted:
                        pygame.time.Clock().tick(10)
                    
                    # Unload the music and add a small delay
                    pygame.mixer.music.unload()
                    time.sleep(0.1)
                    
                finally:
                    # Try to remove the file after playing
                    try:
                        if os.path.exists(self.current_audio_file):
                            os.remove(self.current_audio_file)
                    except Exception:
                        pass  # Ignore deletion errors during playback
                
        except Exception as e:
            print(f"Speech error: {e}")
        finally:
            self.is_speaking = False
            self.current_audio_file = None
  


    def speak(self, text, priority=False):
        """
        Add text to the speech queue
        
        Args:
            text (str): Text to be spoken
            priority (bool): Whether this speech has priority
        """
        if text and not self.should_stop and not self.is_muted:
            self.speech_queue.put((text, priority))

    def wait_until_done(self):
        """Wait until all speech is complete"""
        while self.is_speaking or not self.speech_queue.empty():
            time.sleep(0.1)

    def toggle_mute(self):
        """
        Toggle mute state
        
        Returns:
            bool: New mute state
        """
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.unload()
            self.speech_queue.queue.clear()
        return self.is_muted

    def unmute(self):
        """Unmute audio output"""
        self.is_muted = False
        self.speak("Voice output restored")

    """def stop(self):
        Stop all audio operations and cleanup
        self.should_stop = True
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.unload()
        self.speech_queue.queue.clear()
        time.sleep(0.2)  # Give a small delay for cleanup
        self._cleanup_old_files()
        pygame.mixer.quit()
        """
    # Ai mute app 
    def stop(self):
        """Stop all AI speech immediately"""
        try:
            # Clear speech queue
            self.speech_queue.queue.clear()
            
            # Stop current speech playback
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            
            # Reset speech state
            self.is_speaking = False
            self.current_audio_file = None
            
        except Exception as e:
            print(f"Error stopping audio: {e}")

    def toggle_mute(self):
        """Toggle AI speech mute state"""
        try:
            self.is_muted = not self.is_muted
            if self.is_muted:
                # Stop any current speech
                self.stop()
                
            return self.is_muted
        except Exception as e:
            print(f"Error toggling mute: {e}")
            return False  