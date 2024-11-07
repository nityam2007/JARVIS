import subprocess
import webbrowser
import time
import keyboard
import pyautogui
import psutil
import win32gui
import win32con
import win32process
import win32com.client
from typing import Dict, Tuple, Optional
import os
from pathlib import Path
from .spotify_controller import SpotifyController

class SystemController:
    """
    Handles system-level operations including application control, 
    window management, and text input
    """
    def __init__(self, config):
        """Initialize the SystemController"""
        self.config = config
        self.all_apps = {}
        # Combine all application categories into one dictionary
        for category in config.get("applications", {}).values():
            self.all_apps.update(category)
        
        self.urls = config.get("urls", {})
        self.hotkeys = config.get("hotkeys", {})
        self.active_windows: Dict[str, int] = {}
        self.shell = win32com.client.Dispatch("WScript.Shell")
        self.current_app = None
        
        # Initialize Spotify controller if path is available
        spotify_path = None
        if 'media' in config.get("applications", {}) and 'spotify' in config["applications"]["media"]:
            spotify_path = config["applications"]["media"]["spotify"]
        self.spotify = SpotifyController(spotify_path) if spotify_path else None
        
        # Configure pyautogui settings
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1
        
        # Register hotkeys
        self.register_hotkeys()

    def execute_system_command(self, command: str) -> Tuple[bool, str]:
        """
        Execute a system command safely
        
        Args:
            command (str): System command to execute
            
        Returns:
            Tuple[bool, str]: Success status and message
        """
        try:
            if command.lower().startswith(("shutdown", "restart", "rundll32")):
                # These are safe system commands from config
                subprocess.run(command, shell=True, check=True)
                return True, "System command executed successfully"
            else:
                return False, "Unauthorized system command"
        except subprocess.CalledProcessError as e:
            return False, f"Error executing command: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def _fix_app_path(self, app_path: str) -> str:
        """Resolve and fix application path"""
        if app_path.endswith('.exe') or '\\' in app_path:
            # If it's a full path or explicit exe, return as is
            return app_path
        
        # For simple commands like 'notepad', 'calc', etc.
        return f"{app_path}.exe"

    def register_hotkeys(self):
        """Register system-wide hotkeys for various controls"""
        try:
            # System hotkeys from config
            if "system" in self.hotkeys:
                for action, hotkey in self.hotkeys["system"].items():
                    try:
                        keyboard.add_hotkey(hotkey, lambda a=action: self._handle_system_hotkey(a))
                    except Exception as e:
                        print(f"Warning: Could not register system hotkey {hotkey}: {e}")
            
            # Media control hotkeys
            if "spotify" in self.hotkeys:
                for action, hotkey in self.hotkeys["spotify"].items():
                    try:
                        keyboard.add_hotkey(hotkey, lambda a=action: self.control_spotify(a))
                    except Exception as e:
                        print(f"Warning: Could not register spotify hotkey {hotkey}: {e}")
        except Exception as e:
            print(f"Warning: Error registering hotkeys: {e}")

    def _handle_system_hotkey(self, action: str):
        """Handle system hotkey actions"""
        try:
            if action == "close_window":
                keyboard.send('alt+f4')
            elif action == "switch_window":
                keyboard.send('alt+tab')
            elif action == "show_desktop":
                keyboard.send('win+d')
            elif action == "lock_pc":
                keyboard.send('win+l')
            elif action == "screenshot":
                keyboard.send('win+shift+s')
        except Exception as e:
            print(f"Error handling system hotkey {action}: {e}")

    def handle_music_command(self, command: str) -> Tuple[bool, str]:
        """Handle music-related commands"""
        if not self.spotify:
            return False, "Spotify controller not initialized"

        command = command.lower()

        # Handle play commands
        if "play" in command:
            # Generic play command
            if command in ["play", "play music", "play song", "play something"]:
                return self.spotify.play_random_music()

            # Play specific artist/genre
            search_term = command.replace("play", "").strip()
            if search_term:
                try:
                    # Focus or launch Spotify
                    success, msg = self.spotify.launch_spotify()
                    if not success:
                        return False, msg

                    # Search for the term
                    keyboard.press_and_release('ctrl+l')
                    time.sleep(0.5)
                    keyboard.press_and_release('ctrl+a')
                    keyboard.press_and_release('delete')
                    time.sleep(0.5)
                    
                    for char in search_term:
                        pyautogui.write(char)
                        time.sleep(0.1)
                    
                    time.sleep(0.5)
                    keyboard.press_and_release('enter')
                    time.sleep(2)

                    # Select and play
                    keyboard.press_and_release('tab')
                    time.sleep(0.3)
                    keyboard.press_and_release('enter')
                    
                    return True, f"Playing {search_term}"
                except Exception as e:
                    return False, f"Error playing {search_term}: {e}"

        # Handle playback controls
        if command in ["pause", "pause music", "stop music"]:
            return self.spotify.control_playback("pause")
        
        if command in ["resume", "resume music", "continue music"]:
            return self.spotify.control_playback("play")
            
        if any(word in command for word in ["next", "next song", "skip"]):
            return self.spotify.control_playback("next_track")
            
        if any(word in command for word in ["previous", "previous song", "back"]):
            return self.spotify.control_playback("previous_track")

        # Handle volume controls
        if "volume up" in command or "louder" in command:
            return self.spotify.adjust_volume("up")
            
        if "volume down" in command or "quieter" in command:
            return self.spotify.adjust_volume("down")

        # Handle seeking
        if "forward" in command:
            return self.spotify.quick_seek("forward")
            
        if "backward" in command or "back" in command:
            return self.spotify.quick_seek("backward")

        # Handle close command
        if "close" in command:
            return self.spotify.close_spotify()

        return False, "Unknown music command"

    def find_window_by_title(self, title_fragment: str) -> Optional[int]:
        """Find window handle by partial title match"""
        def callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if window_title and title_fragment.lower() in window_title.lower():
                    results.append(hwnd)
            return True

        found_windows = []
        win32gui.EnumWindows(callback, found_windows)
        return found_windows[0] if found_windows else None

    def open_application(self, app_name: str, write_text: str = None) -> Tuple[bool, str]:
        """
        Open application and optionally write text
        
        Args:
            app_name (str): Name of the application to open
            write_text (str, optional): Text to write after opening
        """
        app_name = app_name.lower()
        
        # Check if we have a path for this app
        if app_name not in self.all_apps:
            return False, f"Application {app_name} not found in configuration"
            
        app_path = self._fix_app_path(self.all_apps[app_name])
        
        try:
            # Open new instance
            process = subprocess.Popen(app_path)
            time.sleep(1.5)  # Wait longer for window to appear
            
            # Find and store window handle
            if hwnd := self.find_window_by_title(app_name):
                self.active_windows[app_name] = hwnd
                self.current_app = app_name
                
                # Focus window
                self.focus_window(app_name)
                
                # Write text if provided
                if write_text:
                    time.sleep(0.5)  # Wait for window to be ready
                    pyautogui.write(write_text)
                    return True, f"Opened {app_name} and wrote text"
                
                return True, f"Opened {app_name}"
        except Exception as e:
            return False, f"Error opening {app_name}: {e}"

    def write_to_current_app(self, text: str) -> Tuple[bool, str]:
        """Write text to currently focused application"""
        try:
            if self.current_app:
                self.focus_window(self.current_app)
                time.sleep(0.2)
                pyautogui.write(text)
                return True, f"Text written to {self.current_app}"
            else:
                return False, "No active application to write to"
        except Exception as e:
            return False, f"Error writing text: {e}"

    def close_application(self, app_name: str) -> Tuple[bool, str]:
        """Close application by name"""
        app_name = app_name.lower()
        
        # First try to close by window handle
        if app_name in self.active_windows:
            try:
                hwnd = self.active_windows[app_name]
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.5)
                
                # Clean up references
                if self.current_app == app_name:
                    self.current_app = None
                del self.active_windows[app_name]
                return True, f"Closed {app_name}"
            except Exception as e:
                print(f"Error closing window: {e}")

        # Try to find and close window by title
        if hwnd := self.find_window_by_title(app_name):
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.5)
                if self.current_app == app_name:
                    self.current_app = None
                return True, f"Closed {app_name}"
            except Exception as e:
                return False, f"Error closing {app_name}: {e}"

        # Try to close by process name
        for proc in psutil.process_iter(['name']):
            try:
                if app_name in proc.info['name'].lower():
                    proc.terminate()
                    time.sleep(0.5)
                    if self.current_app == app_name:
                        self.current_app = None
                    return True, f"Terminated {app_name}"
            except:
                continue

        return False, f"Could not find {app_name} to close"

    def minimize_window(self, app_name: str) -> Tuple[bool, str]:
        """Minimize window by application name"""
        if hwnd := self.find_window_by_title(app_name):
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True, f"Minimized {app_name}"
        return False, f"Could not find {app_name} to minimize"

    def maximize_window(self, app_name: str) -> Tuple[bool, str]:
        """Maximize window by application name"""
        if hwnd := self.find_window_by_title(app_name):
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True, f"Maximized {app_name}"
        return False, f"Could not find {app_name} to maximize"

    def focus_window(self, app_name: str) -> Tuple[bool, str]:
        """Bring window to front"""
        if hwnd := self.find_window_by_title(app_name):
            try:
                # Force focus
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True, f"Focused {app_name}"
            except Exception as e:
                return False, f"Error focusing {app_name}: {e}"
        return False, f"Could not find {app_name} to focus"

    def open_website(self, site_name: str) -> Tuple[bool, str]:
        """Open website in default browser"""
        site_name = site_name.lower()
        if site_name in self.urls:
            try:
                webbrowser.open(self.urls[site_name])
                return True, f"Opening {site_name}"
            except Exception as e:
                return False, f"Error opening {site_name}: {e}"
        return False, f"Website {site_name} not configured"

    def control_spotify(self, command: str) -> Tuple[bool, str]:
        """Control Spotify playback"""
        try:
            if "spotify" in self.hotkeys and command in self.hotkeys["spotify"]:
                keyboard.press_and_release(self.hotkeys["spotify"][command])
                return True, f"Spotify {command} executed"
            return False, "Unknown Spotify command"
        except Exception as e:
            return False, f"Error controlling Spotify: {e}"

    def get_system_info(self) -> dict:
        """Get system information"""
        try:
            import platform
            return {
                "os": platform.platform(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "active_windows": len(self.active_windows),
                "current_app": self.current_app
            }
        except Exception as e:
            print(f"Error getting system info: {e}")
            return {}