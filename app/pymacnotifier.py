import subprocess
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

    def notify(
        self,
        message: str,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        sound: Optional[NotificationSound] = None,
        url: Optional[str] = None,
        group: Optional[str] = None,
        timeout: Optional[int] = None,
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

        try:
            result = subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def simple_notify(self, message: str, title: Optional[str] = None) -> bool:
        """
        Send a simple notification with just message and title.

        Args:
            message: The notification message
            title: The notification title (uses default_title if not provided)

        Returns:
            bool: True if notification was sent successfully
        """
        return self.notify(
            message=message, title=title, sound=NotificationSound.DEFAULT
        )
