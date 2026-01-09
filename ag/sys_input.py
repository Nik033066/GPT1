import ctypes
import ctypes.util
import sys
import time
from typing import Any, Callable, cast

# macOS CoreGraphics constants
kCGEventMouseMoved = 5
kCGEventLeftMouseDown = 1
kCGEventLeftMouseUp = 2
kCGMouseButtonLeft = 0
kCGHIDEventTap = 0

class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

_cg: Any | None = None
_CGEventCreateMouseEvent: Any | None = None
_CGEventPost: Any | None = None
_CFRelease: Any | None = None

def _init_macos() -> bool:
    global _cg, _CGEventCreateMouseEvent, _CGEventPost, _CFRelease
    if _cg:
        return True
    try:
        path = ctypes.util.find_library('CoreGraphics')
        if not path:
            return False
        _cg = ctypes.CDLL(path)
        
        _CGEventCreateMouseEvent = _cg.CGEventCreateMouseEvent
        _CGEventCreateMouseEvent.restype = ctypes.c_void_p
        _CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32]
        
        _CGEventPost = _cg.CGEventPost
        _CGEventPost.restype = None
        _CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]

        # CFRelease is in CoreFoundation, but often available in CoreGraphics link or separate load
        # We try to load CoreFoundation separately just in case
        cf_path = ctypes.util.find_library('CoreFoundation')
        if cf_path:
            cf = ctypes.CDLL(cf_path)
            _CFRelease = cf.CFRelease
            _CFRelease.argtypes = [ctypes.c_void_p]
            _CFRelease.restype = None
        
        return True
    except Exception:
        return False

def move(x: float, y: float) -> None:
    """Muove il cursore fisico alle coordinate globali (x, y) usando CoreGraphics."""
    if sys.platform != "darwin":
        return
    if not _init_macos():
        return
    
    create_evt = cast(Callable[..., Any], _CGEventCreateMouseEvent)
    post_evt = cast(Callable[..., Any], _CGEventPost)
    pt = CGPoint(x, y)
    evt = create_evt(None, kCGEventMouseMoved, pt, kCGMouseButtonLeft)
    if evt:
        post_evt(kCGHIDEventTap, evt)
        if _CFRelease:
            cast(Callable[[Any], Any], _CFRelease)(evt)

def click(x: float, y: float) -> None:
    """Esegue un click sinistro fisico alle coordinate globali (x, y)."""
    if sys.platform != "darwin":
        return
    if not _init_macos():
        return

    create_evt = cast(Callable[..., Any], _CGEventCreateMouseEvent)
    post_evt = cast(Callable[..., Any], _CGEventPost)
    pt = CGPoint(x, y)
    
    # Mouse Down
    evt_down = create_evt(None, kCGEventLeftMouseDown, pt, kCGMouseButtonLeft)
    if evt_down:
        post_evt(kCGHIDEventTap, evt_down)
        if _CFRelease:
            cast(Callable[[Any], Any], _CFRelease)(evt_down)
    
    time.sleep(0.05) # Piccolo delay realistico
    
    # Mouse Up
    evt_up = create_evt(None, kCGEventLeftMouseUp, pt, kCGMouseButtonLeft)
    if evt_up:
        post_evt(kCGHIDEventTap, evt_up)
        if _CFRelease:
            cast(Callable[[Any], Any], _CFRelease)(evt_up)
