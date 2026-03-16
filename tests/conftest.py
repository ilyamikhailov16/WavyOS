import sys
import types


def _ensure_module(name: str, module: types.ModuleType) -> None:
    if name not in sys.modules:
        sys.modules[name] = module


keyboard_module = types.ModuleType("keyboard")
keyboard_module.add_hotkey = lambda *args, **kwargs: None
keyboard_module.wait = lambda *args, **kwargs: None
_ensure_module("keyboard", keyboard_module)

cv2_module = types.ModuleType("cv2")
cv2_module.COLOR_BGRA2BGR = 1
cv2_module.VideoWriter_fourcc = lambda *args: 0
cv2_module.VideoWriter = lambda *args, **kwargs: None
cv2_module.cvtColor = lambda frame, code: frame
_ensure_module("cv2", cv2_module)

numpy_module = types.ModuleType("numpy")
numpy_module.array = lambda value: value
_ensure_module("numpy", numpy_module)

mss_module = types.ModuleType("mss")
mss_module.mss = lambda: None
_ensure_module("mss", mss_module)

pyautogui_module = types.ModuleType("pyautogui")
pyautogui_module.screenshot = lambda: None
pyautogui_module.press = lambda *args, **kwargs: None
pyautogui_module.hotkey = lambda *args, **kwargs: None
pyautogui_module.write = lambda *args, **kwargs: None
_ensure_module("pyautogui", pyautogui_module)

send2trash_module = types.ModuleType("send2trash")
send2trash_module.send2trash = lambda *args, **kwargs: None
_ensure_module("send2trash", send2trash_module)

pythoncom_module = types.ModuleType("pythoncom")
pythoncom_module.CoInitialize = lambda: None
pythoncom_module.CoUninitialize = lambda: None
_ensure_module("pythoncom", pythoncom_module)