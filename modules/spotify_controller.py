import time
import random
import pyautogui
import win32gui
import win32con
import win32process
import subprocess
import keyboard
import os
from typing import Tuple, Optional, List
import psutil

class SpotifyController:
    """Enhanced Spotify Controller with improved search and playback controls"""
    
    def __init__(self, spotify_path: str):
        """Initialize SpotifyController"""
        self.spotify_path = spotify_path
        self.is_playing = False
        self.is_muted = False
        self.spotify_hwnd = None
        self.last_window_title = None
        self.previous_window = None  # Store previous active window
        self.last_volume = 50
        
        # Configure PyAutoGUI settings
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.3
        
        # Enhanced keyboard shortcuts
        self.shortcuts = {
            'play_pause': 'space',
            'next_track': 'ctrl+right',
            'previous_track': 'ctrl+left',
            'volume_up': 'ctrl+up',
            'volume_down': 'ctrl+down',
            'seek_forward': 'ctrl+shift+right',
            'seek_backward': 'ctrl+shift+left',
            'shuffle': 'ctrl+s',
            'repeat': 'ctrl+r',
            'like': 'ctrl+b',
            'search': 'ctrl+l',
            'minimize': 'alt+m',
            'fullscreen': 'f11'
        }

        # Category mappings with proper order
        self.categories = {
            'all': 0,
            'playlists': 1,
            'songs': 2,
            'artists': 3,
            'albums': 4
        }

        # Find Spotify installation
        self._verify_spotify_path()
        
        # Check if Spotify is running and find window
        if self._is_spotify_running():
            self.spotify_hwnd = self._find_spotify_window()

    def _verify_spotify_path(self):
        """Verify Spotify installation path exists"""
        if not os.path.exists(self.spotify_path):
            alt_paths = [
                f"C:\\Users\\{os.getenv('USERNAME')}\\AppData\\Roaming\\Spotify\\Spotify.exe",
                "C:\\Program Files\\Spotify\\Spotify.exe",
                "C:\\Program Files (x86)\\Spotify\\Spotify.exe"
            ]
            
            for path in alt_paths:
                if os.path.exists(path):
                    self.spotify_path = path
                    print(f"Found Spotify at: {path}")
                    break
            else:
                print("Warning: Could not find Spotify installation")

    def _get_spotify_process_id(self) -> Optional[int]:
        """Get Spotify process ID."""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == 'spotify.exe':
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _find_spotify_window(self) -> Optional[int]:
        """Find Spotify window handle."""
        spotify_pid = self._get_spotify_process_id()
        if not spotify_pid:
            return None

        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == spotify_pid:  # Match Spotify's process ID
                    title = win32gui.GetWindowText(hwnd)
                    if 'spotify' in title.lower():  # Ensure window title contains 'Spotify'
                        windows.append((hwnd, title))
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            windows.sort(key=lambda x: len(x[1]))
            for hwnd, title in windows:
                if 'spotify' in title.lower():
                    return hwnd
            return windows[0][0]  # Fallback to the first Spotify window found

        return None
        

    def _ensure_window_focus(self, retries: int = 5) -> bool:
        """Ensure Spotify window has focus with enhanced reliability"""
        print("Attempting to focus Spotify window...")
        
        for attempt in range(retries):
            try:
                # Find or verify window
                if not self.spotify_hwnd:
                    self.spotify_hwnd = self._find_spotify_window()
                    if not self.spotify_hwnd:
                        print(f"Attempt {attempt + 1}: Window not found")
                        time.sleep(0.5)
                        continue

                # Store current active window
                try:
                    self.previous_window = win32gui.GetForegroundWindow()
                except:
                    self.previous_window = None

                # Restore window if minimized
                if win32gui.IsIconic(self.spotify_hwnd):
                    win32gui.ShowWindow(self.spotify_hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)

                # Multiple focus attempts
                for _ in range(3):
                    try:
                        # Force foreground window
                        win32gui.BringWindowToTop(self.spotify_hwnd)
                        win32gui.SetForegroundWindow(self.spotify_hwnd)
                        time.sleep(0.2)
                        
                        # Verify focus
                        if win32gui.GetForegroundWindow() == self.spotify_hwnd:
                            print("Successfully focused Spotify window")
                            return True
                    except:
                        pass
                    time.sleep(0.2)

                print(f"Focus attempt {attempt + 1} failed")
                time.sleep(0.3)

            except Exception as e:
                print(f"Focus error on attempt {attempt + 1}: {e}")
                self.spotify_hwnd = None
                time.sleep(0.3)

        print("Failed to focus Spotify window after all attempts")
        return False

    def _release_focus(self):
        """Release focus back to previous window"""
        try:
            if self.previous_window and win32gui.IsWindow(self.previous_window):
                try:
                    win32gui.SetForegroundWindow(self.previous_window)
                    time.sleep(0.1)
                except:
                    pass
        except:
            pass

    def _is_spotify_running(self) -> bool:
        """Check if Spotify process is running"""
        return self._get_spotify_process_id() is not None
    
    def launch_spotify(self) -> Tuple[bool, str]:
        """Launch Spotify application with enhanced window handling"""
        try:
            # Check if already running
            if self._is_spotify_running():
                print("Spotify is running, finding window...")
                self.spotify_hwnd = self._find_spotify_window()
                if self.spotify_hwnd and self._ensure_window_focus():
                    self._release_focus()
                    return True, "Spotify is already running"

            print("Launching Spotify...")
            # Kill any existing processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == 'spotify.exe':
                        proc.kill()
                        time.sleep(0.5)
                except:
                    continue

            # Launch new instance
            subprocess.Popen(self.spotify_path)
            
            # Wait for launch with increased timeout
            for i in range(15):  # 15 seconds timeout
                time.sleep(1)
                print(f"Waiting for Spotify... ({i+1}/15)")
                
                if self._is_spotify_running():
                    self.spotify_hwnd = self._find_spotify_window()
                    if self.spotify_hwnd and self._ensure_window_focus():
                        self._release_focus()
                        return True, "Launched Spotify successfully"
            
            return False, "Failed to launch Spotify"
            
        except Exception as e:
            print(f"Launch error: {e}")
            return False, f"Error launching Spotify: {e}"

    def control_playback(self, command: str) -> Tuple[bool, str]:
        """Control Spotify playback with enhanced reliability"""
        try:
            if not self._is_spotify_running():
                return False, "Spotify is not running"

            print(f"Executing playback command: {command}")
            
            # Multiple focus attempts for reliability
            focus_attempts = 3
            for attempt in range(focus_attempts):
                if self._ensure_window_focus():
                    try:
                        # Execute command
                        if command in ["play", "pause", "play_pause"]:
                            keyboard.press_and_release(self.shortcuts['play_pause'])
                            time.sleep(0.2)
                            self.is_playing = not self.is_playing
                            status = "paused" if not self.is_playing else "playing"
                            self._release_focus()
                            return True, f"Music {status}"

                        elif command in ["next", "skip"]:
                            keyboard.press_and_release(self.shortcuts['next_track'])
                            time.sleep(0.2)
                            self._release_focus()
                            return True, "Skipped to next track"
                            
                        elif command in ["previous", "back"]:
                            keyboard.press_and_release(self.shortcuts['previous_track'])
                            time.sleep(0.2)
                            self._release_focus()
                            return True, "Previous track"

                        elif command == "shuffle":
                            keyboard.press_and_release(self.shortcuts['shuffle'])
                            time.sleep(0.2)
                            self._release_focus()
                            return True, "Toggled shuffle"
                            
                        elif command == "repeat":
                            keyboard.press_and_release(self.shortcuts['repeat'])
                            time.sleep(0.2)
                            self._release_focus()
                            return True, "Toggled repeat"
                            
                        elif command == "like":
                            keyboard.press_and_release(self.shortcuts['like'])
                            time.sleep(0.2)
                            self._release_focus()
                            return True, "Toggled like status"
                        
                        else:
                            self._release_focus()
                            return False, f"Unknown command: {command}"
                            
                    except Exception as e:
                        print(f"Command execution error: {e}")
                        if attempt < focus_attempts - 1:
                            print(f"Retrying... (attempt {attempt + 2}/{focus_attempts})")
                            time.sleep(0.5)
                            continue
                        return False, f"Command failed: {str(e)}"
                else:
                    if attempt < focus_attempts - 1:
                        print(f"Focus failed, retrying... (attempt {attempt + 2}/{focus_attempts})")
                        time.sleep(0.5)
                        continue
                    
            return False, "Could not focus Spotify after multiple attempts"
            
        except Exception as e:
            print(f"Playback control error: {e}")
            return False, f"Error controlling playback: {e}"

    def search_and_play(self, query: str, category: str = 'all') -> Tuple[bool, str]:
        """Enhanced search and play with better reliability"""
        try:
            # Ensure Spotify is running
            if not self._is_spotify_running():
                success, msg = self.launch_spotify()
                if not success:
                    return False, msg

            print(f"Searching for: {query} in category: {category}")
            if not self._ensure_window_focus():
                return False, "Could not focus Spotify window"

            # Clear and focus search
            keyboard.press_and_release(self.shortcuts['search'])
            time.sleep(0.3)
            keyboard.press_and_release('ctrl+a')
            keyboard.press_and_release('backspace')
            time.sleep(0.2)

            # Type search query
            for char in query:  # Type character by character for reliability
                keyboard.write(char)
                time.sleep(0.05)
            time.sleep(1.0)  # Wait for search results

            # Handle category selection
            if category != 'all' and category in self.categories:
                # Navigate to filters
                keyboard.press_and_release('tab')
                time.sleep(0.2)
                
                # Select category
                for _ in range(self.categories[category]):
                    keyboard.press_and_release('right')
                    time.sleep(0.2)

                keyboard.press_and_release('enter')
                time.sleep(0.5)

            # Navigate to first result
            keyboard.press_and_release('tab')
            time.sleep(0.3)
            keyboard.press_and_release('enter')
            time.sleep(0.5)

            # Ensure playback starts
            keyboard.press_and_release(self.shortcuts['play_pause'])
            self.is_playing = True
            
            self._release_focus()
            return True, f"Playing {query}"
            
        except Exception as e:
            print(f"Search error: {e}")
            return False, f"Error during search: {e}"

    def adjust_volume(self, direction: str = "up", amount: int = 2) -> Tuple[bool, str]:
        """Adjust Spotify volume with better reliability"""
        try:
            if not self._ensure_window_focus():
                return False, "Could not focus Spotify window"

            amount = max(1, min(10, amount))  # Limit to 1-10 steps
            shortcut = self.shortcuts['volume_up'] if direction == "up" else self.shortcuts['volume_down']
            
            for _ in range(amount):
                keyboard.press_and_release(shortcut)
                time.sleep(0.1)

            self._release_focus()
            return True, f"Volume adjusted {direction}"
        except Exception as e:
            print(f"Volume error: {e}")
            return False, f"Error adjusting volume: {e}"

    def play_random_music(self) -> Tuple[bool, str]:
        """Play random music with better playlist selection"""
        try:
            search_terms = [
                "today's top hits", "discover weekly", 
                "release radar", "daily mix 1",
                "viral hits", "popular playlists",
                "mood booster", "top 50 global",
                "hit rewind", "all out 2000s"
            ]
            term = random.choice(search_terms)
            print(f"Selected random playlist: {term}")
            return self.search_and_play(term, 'playlists')
        except Exception as e:
            print(f"Random play error: {e}")
            return False, f"Error playing random music: {e}"

    def close_spotify(self) -> Tuple[bool, str]:
        """Close Spotify with enhanced cleanup"""
        try:
            # Try graceful window close first
            if self.spotify_hwnd:
                try:
                    win32gui.PostMessage(self.spotify_hwnd, win32con.WM_CLOSE, 0, 0)
                    time.sleep(1)
                except:
                    pass

            # Force close if still running
            spotify_pid = self._get_spotify_process_id()
            if spotify_pid:
                try:
                    process = psutil.Process(spotify_pid)
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    # Kill if terminate fails
                    try:
                        process.kill()
                        process.wait(timeout=5)
                    except:
                        pass

            self.spotify_hwnd = None
            self.is_playing = False
            self.last_window_title = None
            
            # Verify process is gone
            if not self._is_spotify_running():
                return True, "Closed Spotify successfully"
            return False, "Failed to close Spotify completely"
            
        except Exception as e:
            print(f"Close error: {e}")
            return False, f"Error closing Spotify: {e}"

    def minimize_window(self) -> Tuple[bool, str]:
        """Minimize Spotify window"""
        try:
            if not self.spotify_hwnd:
                self.spotify_hwnd = self._find_spotify_window()
            
            if self.spotify_hwnd:
                win32gui.ShowWindow(self.spotify_hwnd, win32con.SW_MINIMIZE)
                return True, "Minimized Spotify window"
            return False, "Spotify window not found"
        except Exception as e:
            print(f"Minimize error: {e}")
            return False, f"Error minimizing window: {e}"

    def restore_window(self) -> Tuple[bool, str]:
        """Restore Spotify window"""
        try:
            if not self.spotify_hwnd:
                self.spotify_hwnd = self._find_spotify_window()
            
            if self.spotify_hwnd:
                win32gui.ShowWindow(self.spotify_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.spotify_hwnd)
                time.sleep(0.2)
                self._release_focus()
                return True, "Restored Spotify window"
            return False, "Spotify window not found"
        except Exception as e:
            print(f"Restore error: {e}")
            return False, f"Error restoring window: {e}"