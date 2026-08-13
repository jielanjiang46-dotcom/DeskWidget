import ctypes
import sys


class _AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class _WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def apply_window_effect(
    widget, enabled: bool, opacity: int, tint_color: str = "#F8F9FC"
) -> None:
    """Apply native blur without fading child controls or text."""
    widget.setWindowOpacity(1.0)
    if sys.platform != "win32":
        return
    try:
        color = tint_color.lstrip("#")
        red, green, blue = (int(color[index:index + 2], 16) for index in (0, 2, 4))
        policy = _AccentPolicy()
        # Acrylic supplies its own tinted composition surface. Plain blur-behind
        # can expose Qt's transparent backing surface as black on Windows 11.
        policy.AccentState = 4 if enabled else 0  # ACRYLICBLURBEHIND / DISABLED
        policy.AccentFlags = 2
        alpha = int(255 * opacity / 100) if enabled else 255
        # GradientColor is AABBGGRR, not ARGB.
        policy.GradientColor = (
            (alpha << 24) | (blue << 16) | (green << 8) | red
        )
        data = _WindowCompositionAttributeData(
            19, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p), ctypes.sizeof(policy)
        )
        setter = ctypes.windll.user32.SetWindowCompositionAttribute
        setter.argtypes = [ctypes.c_void_p, ctypes.POINTER(_WindowCompositionAttributeData)]
        setter.restype = ctypes.c_int
        window = ctypes.c_void_p(int(widget.winId()))
        if enabled:
            disabled = _AccentPolicy(0, 0, 0, 0)
            disabled_data = _WindowCompositionAttributeData(
                19,
                ctypes.cast(ctypes.pointer(disabled), ctypes.c_void_p),
                ctypes.sizeof(disabled),
            )
            setter(window, ctypes.byref(disabled_data))
        setter(window, ctypes.byref(data))
        try:
            ctypes.windll.dwmapi.DwmFlush()
        except (AttributeError, OSError):
            pass
        widget.update()
        widget.repaint()
    except (AttributeError, OSError, ValueError, OverflowError):
        pass
