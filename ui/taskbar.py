"""
Progress on the Windows taskbar button (ITaskbarList3), via plain ctypes COM.
Silently does nothing on other platforms or if COM isn't available.
"""
import ctypes
import sys
from ctypes import wintypes

TBPF_NOPROGRESS, TBPF_INDETERMINATE, TBPF_NORMAL, TBPF_ERROR, TBPF_PAUSED = 0, 1, 2, 4, 8


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8)]

    def __init__(self, s):
        super().__init__()
        ctypes.oledll.ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(self))


class TaskbarProgress:
    def __init__(self, widget):
        self._widget = widget
        self._ptr = None
        if sys.platform != 'win32':
            return
        try:
            ole32 = ctypes.oledll.ole32
            ole32.CoInitialize(None)
            clsid = _GUID("{56FDF344-FD6D-11d0-958A-006097C9A090}")   # TaskbarList
            iid = _GUID("{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}")     # ITaskbarList3
            ptr = ctypes.c_void_p()
            ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(ptr))
            self._ptr = ptr
            self._call(3, ctypes.HRESULT)  # HrInit
        except Exception:
            self._ptr = None

    def _call(self, index, restype, *args):
        vtable = ctypes.cast(ctypes.cast(self._ptr, ctypes.POINTER(ctypes.c_void_p))[0],
                             ctypes.POINTER(ctypes.c_void_p))
        argtypes = [ctypes.c_void_p] + [type(a) for a in args]
        fn = ctypes.WINFUNCTYPE(restype, *argtypes)(vtable[index])
        return fn(self._ptr, *args)

    def _hwnd(self):
        return wintypes.HWND(int(self._widget.winId()))

    def set_value(self, done, total):
        if not self._ptr:
            return
        try:
            self._call(10, ctypes.HRESULT, self._hwnd(), ctypes.c_int(TBPF_NORMAL))
            self._call(9, ctypes.HRESULT, self._hwnd(), ctypes.c_ulonglong(done), ctypes.c_ulonglong(max(total, 1)))
        except Exception:
            pass

    def set_state(self, state):
        if not self._ptr:
            return
        try:
            self._call(10, ctypes.HRESULT, self._hwnd(), ctypes.c_int(state))
        except Exception:
            pass

    def clear(self):
        self.set_state(TBPF_NOPROGRESS)
