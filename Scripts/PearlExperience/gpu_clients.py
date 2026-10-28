# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
import ctypes,subprocess
from pathlib import Path

def process_names():
    """Toolhelp exposes image basenames even when protected DWM paths are hidden."""
    from ctypes import wintypes as w
    class Entry(ctypes.Structure):
        _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),
                  ('heap',ctypes.c_size_t),('module',w.DWORD),('threads',w.DWORD),
                  ('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),
                  ('name',w.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
    kernel.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    names={}
    try:
        entry=Entry();entry.size=ctypes.sizeof(Entry)
        ok=kernel.Process32FirstW(handle,ctypes.byref(entry))
        while ok:
            names[int(entry.pid)]=entry.name.lower()
            ok=kernel.Process32NextW(handle,ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return names

def gpu_processes():
    result = subprocess.run(['C:/Windows/System32/nvidia-smi.exe',
                             '--query-compute-apps=pid,process_name', '--format=csv,noheader'],
                            capture_output=True, text=True, timeout=8,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Cannot inspect other GPU processes')
    processes = {}
    for line in result.stdout.splitlines():
        fields = line.split(',', 1)
        if len(fields) == 2 and fields[0].strip().isdigit():
            processes[int(fields[0].strip())] = Path(fields[1].strip()).name.lower()
    if any(name.startswith('[') for name in processes.values()):
        names = process_names()
        processes = {pid: names.get(pid, name) if name.startswith('[') else name
                     for pid, name in processes.items()}
    return processes

DESKTOP_PROCESSES = {'dwm.exe', 'explorer.exe', 'shellhost.exe', 'msedge.exe',
                     'msedgewebview2.exe', 'chrome.exe', 'chatgpt.exe',
                     'applicationframehost.exe', 'textinputhost.exe', 'tabtip.exe',
                     'logonui.exe', 'armourycrate.exe', 'gameviewer.exe',
                     'phoneexperiencehost.exe', 'realtekaudiocontrol.exe',
                     'crossdeviceresume.exe', 'systemsettings.exe'}
