import platform
# TODO: Add support for Windows and Linux
if platform.system() != "Darwin":
    raise ImportError("This module only supports macOS")

import time
import io
import AppKit
from PIL import Image
import threading

def save_nsimage(nsimage):
    """
    Convert an NSImage to a Pillow Image in memory.
    Returns a PIL.Image or None on failure.
    """
    # Get TIFF representation first
    tiff_data = nsimage.TIFFRepresentation()
    if tiff_data is None:
        return None

    # Create an NSBitmapImageRep from TIFF data
    bitmap = AppKit.NSBitmapImageRep.imageRepWithData_(tiff_data)
    if bitmap is None:
        return None

    # Get PNG NSData
    png_data = bitmap.representationUsingType_properties_(AppKit.NSPNGFileType, None)
    if png_data is None:
        return None

    # Convert NSData to bytes and load into Pillow
    try:
        raw = png_data.bytes()  # NSData to Python bytes
    except AttributeError:
        raw = bytes(png_data)
    buf = io.BytesIO(raw)
    try:
        image = Image.open(buf)
        return image
    except Exception:
        return None

class ClipboardMonitor:
    """Singleton class to monitor macOS clipboard in background."""
    _instance = None

    def __new__(cls, poll_interval=0.5):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, poll_interval=0.5):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.pb = AppKit.NSPasteboard.generalPasteboard()
        self.last_change = self.pb.changeCount()
        self.poll_interval = poll_interval
        self.last_item = None
        self._running = False
        self.log = False
        self._thread = None

    def start(self, log=False):
        """Start monitoring in a background thread. If log=True, prints each clipboard event."""
        if self._running:
            return
        self.log = log
        self._running = True
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join()

    def _monitor(self):
        while self._running:
            time.sleep(self.poll_interval)
            current_change = self.pb.changeCount()
            if current_change == self.last_change:
                continue
            self.last_change = current_change

            # Try images first
            classes = [AppKit.NSImage]
            objs = self.pb.readObjectsForClasses_options_(classes, None)
            if objs:
                nsimage = objs[0]
                img = save_nsimage(nsimage)
                self.last_item = ('image', img) if img else ('image_failed', None)
                if self.log:
                    print(self.last_item)
                continue

            # Fallback to text
            text = self.pb.stringForType_(AppKit.NSPasteboardTypeString)
            if text:
                self.last_item = ('text', text)
                if self.log:
                    print(self.last_item)
                continue

            # Unsupported types
            types = [str(t) for t in (self.pb.types() or [])]
            self.last_item = ('unsupported', types)
            if self.log:
                print(self.last_item)

    def get_last(self):
        """Return the last clipboard item as a tuple (type, data)."""
        return self.last_item
    
    def copy_text(self, text, rich_text=None):
        """
        Copy text to clipboard. If rich_text bytes are provided, set both plain text and rich text (RTF).
        Args:
            text (str): Plain text to copy to clipboard.
            rich_text (bytes or str, optional): RTF data to copy for rich text formatting.
        """
        pb = self.pb
        pb.clearContents()
        if rich_text is not None:
            # Declare both plain text and RTF types
            types = [AppKit.NSPasteboardTypeString, AppKit.NSPasteboardTypeRTF]
            pb.declareTypes_owner_(types, None)
            pb.setString_forType_(text, AppKit.NSPasteboardTypeString)
            data = rich_text if isinstance(rich_text, (bytes, bytearray)) else rich_text.encode('utf-8')
            nsdata = AppKit.NSData.alloc().initWithBytes_length_(data, len(data))
            pb.setData_forType_(nsdata, AppKit.NSPasteboardTypeRTF)
        else:
            pb.setString_forType_(text, AppKit.NSPasteboardTypeString)

    def copy_image(self, img):
        """
        Copy a PIL.Image to clipboard as an image (PNG).
        Args:
            img (PIL.Image.Image): Image to copy to clipboard.
        """
        pb = self.pb
        pb.clearContents()
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        data = buf.getvalue()
        nsdata = AppKit.NSData.alloc().initWithBytes_length_(data, len(data))
        nsimage = AppKit.NSImage.alloc().initWithData_(nsdata)
        pb.writeObjects_([nsimage])


if __name__ == '__main__':
    monitor = ClipboardMonitor()
    monitor.start(log=True)
    print("Monitoring macOS clipboard. Press Ctrl+C to stop.")
    last = None
    try:
        while True:
            # see if clipboard changed
            if monitor.get_last() != last:
                last = monitor.get_last()
                print("Clipboard changed:", last)
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        print("Stopped by user")


    