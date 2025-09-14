import subprocess
import os
from typing import Optional
from enum import Enum


class NotificationSound(Enum):
    """Available notification sounds on macOS."""

    DEFAULT = "default"
    BASSO = "Basso"
    BLOW = "Blow"
    BOTTLE = "Bottle"
    FROG = "Frog"
    FUNK = "Funk"
    GLASS = "Glass"
    HERO = "Hero"
    MORSE = "Morse"
    PING = "Ping"
    POP = "Pop"
    PURR = "Purr"
    SOSUMI = "Sosumi"
    SUBMARINE = "Submarine"
    TINK = "Tink"


class MacNotifier:
    """A Python wrapper for macOS notifications using terminal-notifier."""

    def __init__(self, default_title: Optional[str] = None):
        """Initialize the notifier with an optional default title."""
        self.default_title = default_title
        self._check_terminal_notifier()

        # Set up paths to icons
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.emojis_dir = os.path.join(current_dir, "assets", "emojis")

        # Define available emotions
        self.available_emotions = {
            "angry",
            "annoyed",
            "excited",
            "happy",
            "love",
            "sad",
            "surprised",
            "thinking",
            "winking",
        }

    def _check_terminal_notifier(self):
        """Check if terminal-notifier is installed."""
        try:
            subprocess.run(
                ["which", "terminal-notifier"], check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "terminal-notifier not found. Install with: brew install terminal-notifier"
            )

    def _get_emoji_path(self, emotion: Optional[str] = None) -> str:
        """
        Get the path to the emoji icon based on emotion.

        Args:
            emotion: The emotion name (e.g., 'happy', 'sad', 'angry')

        Returns:
            str: Path to the emoji file, falls back to default logo if emotion not found
        """
        if emotion and emotion.lower() in self.available_emotions:
            emoji_path = os.path.join(self.emojis_dir, f"{emotion.lower()}.svg")
            if os.path.exists(emoji_path):
                return emoji_path

        # Fallback to happy emoji logo
        return os.path.join(self.emojis_dir, "happy.svg")

    def notify(
        self,
        message: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        sound: Optional[NotificationSound] = None,
        url: Optional[str] = None,
        group: Optional[str] = None,
        timeout: Optional[int] = None,
        high_priority: bool = True,
        emotion: Optional[str] = None,
    ) -> bool:
        """
        Send a notification to macOS Notification Center.

        Args:
            message: The notification message
            title: The notification title (uses default_title if not provided)
            subtitle: The notification subtitle
            sound: The notification sound
            url: URL to open when notification is clicked
            group: Group ID for replacing notifications
            timeout: Timeout in seconds (only works with certain versions)
            high_priority: If True, ignores Do Not Disturb and uses system sender
            emotion: The emotion name for selecting appropriate emoji icon

        Returns:
            bool: True if notification was sent successfully
        """
        cmd = ["terminal-notifier", "-message", message]

        # Use provided title or default
        notification_title = title or self.default_title
        if notification_title:
            cmd.extend(["-title", notification_title])

        if subtitle:
            cmd.extend(["-subtitle", subtitle])

        if sound:
            cmd.extend(["-sound", sound.value])

        if url:
            cmd.extend(["-open", url])

        if group:
            cmd.extend(["-group", group])

        if timeout:
            cmd.extend(["-timeout", str(timeout)])

        # High priority settings to ensure notifications always show
        if high_priority:
            # Ignore Do Not Disturb mode
            cmd.extend(["-ignoreDnD"])
            # Use system sender for higher priority appearance
            cmd.extend(["-sender", "com.apple.systempreferences"])

        # Add the appropriate icon based on emotion
        icon_path = self._get_emoji_path(emotion)
        if os.path.exists(icon_path):
            cmd.extend(["-appIcon", icon_path])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def simple_notify(
        self, message: str, title: Optional[str] = None, emotion: Optional[str] = None
    ) -> bool:
        """
        Send a simple high-priority notification with just message and title.

        Args:
            message: The notification message
            title: The notification title (uses default_title if not provided)
            emotion: The emotion name for selecting appropriate emoji icon

        Returns:
            bool: True if notification was sent successfully
        """
        return self.notify(
            message=message,
            title=title,
            sound=NotificationSound.FUNK,
            high_priority=True,
            emotion=emotion,
        )

    def get_available_emotions(self) -> set:
        """
        Get the set of available emotion names.

        Returns:
            set: Available emotion names
        """
        return self.available_emotions.copy()
