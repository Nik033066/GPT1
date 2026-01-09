from typing import Optional

_pyautogui: Optional[object] = None
_available: Optional[bool] = None


def _init() -> bool:
    global _pyautogui, _available
    if _available is not None:
        return _available
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        _pyautogui = pyautogui
        _available = True
        return True
    except ImportError:
        _available = False
        return False


def is_available() -> bool:
    return _init()


def move(x: float, y: float) -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        _pyautogui.moveTo(int(x), int(y), _pause=False)  # type: ignore
    except Exception:
        pass


def click(x: float, y: float, button: str = "left") -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        _pyautogui.click(int(x), int(y), button=button, _pause=False)  # type: ignore
    except Exception:
        pass


def double_click(x: float, y: float) -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        _pyautogui.doubleClick(int(x), int(y), _pause=False)  # type: ignore
    except Exception:
        pass


def scroll(dy: int, x: Optional[float] = None, y: Optional[float] = None) -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        if x is not None and y is not None:
            _pyautogui.scroll(dy, int(x), int(y), _pause=False)  # type: ignore
        else:
            _pyautogui.scroll(dy, _pause=False)  # type: ignore
    except Exception:
        pass


def type_text(text: str, interval: float = 0.05) -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        _pyautogui.typewrite(text, interval=interval, _pause=False)  # type: ignore
    except Exception:
        pass


def press_key(key: str) -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        _pyautogui.press(key, _pause=False)  # type: ignore
    except Exception:
        pass


def hotkey(*keys: str) -> None:
    if not _init() or _pyautogui is None:
        return
    try:
        _pyautogui.hotkey(*keys, _pause=False)  # type: ignore
    except Exception:
        pass


def get_position() -> tuple[int, int]:
    if not _init() or _pyautogui is None:
        return (0, 0)
    try:
        pos = _pyautogui.position()  # type: ignore
        return (pos.x, pos.y)
    except Exception:
        return (0, 0)


def get_screen_size() -> tuple[int, int]:
    if not _init() or _pyautogui is None:
        return (1920, 1080)
    try:
        size = _pyautogui.size()  # type: ignore
        return (size.width, size.height)
    except Exception:
        return (1920, 1080)
