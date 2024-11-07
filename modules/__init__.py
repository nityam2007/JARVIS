"""
Voice Assistant Modules Package
Includes all core components for the voice assistant
"""

from .audio import AudioManager
from .speech import SpeechRecognitionManager
from .system import SystemController
from .memory import MemoryManager
from .spotify_controller import SpotifyController

__version__ = "1.0.0"
__author__ = "Your Name"

__all__ = [
    'AudioManager',
    'SpeechRecognitionManager',
    'SystemController',
    'MemoryManager',
    'SpotifyController'
]