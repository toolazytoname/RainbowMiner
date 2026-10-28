# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Windows process-handle identity: PID, image and exact creation FILETIME."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import os
from pathlib import Path

K=c.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)]
K.GetProcessTimes.argtypes=[w.HANDLE,c.POINTER(w.FILETIME),c.POINTER(w.FILETIME),c.POINTER(w.FILETIME),c.POINTER(w.FILETIME)]
K.GetCurrentProcess.restype=w.HANDLE
K.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
K.TerminateProcess.argtypes=[w.HANDLE,w.UINT]

def normalized(path):return os.path.normcase(os.path.realpath(str(path)))
def file_hash(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def handle_identity(handle,pid):
    length=w.DWORD(32768);buf=c.create_unicode_buffer(length.value)
    if not K.QueryFullProcessImageNameW(handle,0,buf,c.byref(length)):raise c.WinError(c.get_last_error())
    creation=w.FILETIME();exit_time=w.FILETIME();kernel=w.FILETIME();user=w.FILETIME()
    if not K.GetProcessTimes(handle,c.byref(creation),c.byref(exit_time),c.byref(kernel),c.byref(user)):raise c.WinError(c.get_last_error())
    return {'Pid':int(pid),'Executable':buf.value,'CreationFileTime':(creation.dwHighDateTime<<32)|creation.dwLowDateTime}
def capture_owned_child(process):
    # CPython 3.12 Windows Popen retains the original CreateProcess handle.
    # It cannot accidentally identify a later process that reuses the PID.
    data=handle_identity(int(process._handle),process.pid);data['ParentPid']=os.getpid();return data
def capture_controller():
    data=handle_identity(K.GetCurrentProcess(),os.getpid());data.update(ParentPid=os.getppid(),Sha256=file_hash(data['Executable']));return data

def identity_matches(expected,actual,executable,digest):
    try:
        if type(expected.get('Pid')) is not int or type(expected.get('CreationFileTime')) is not int:return False
        return (expected['Pid']>4 and expected['CreationFileTime']>0 and expected['Pid']==actual['Pid']
                and expected['CreationFileTime']==actual['CreationFileTime']
                and normalized(expected['Executable'])==normalized(executable)==normalized(actual['Executable'])
                and file_hash(actual['Executable'])==digest)
    except (KeyError,TypeError,OSError):return False

class ProcessHandle:
    def __init__(self,pid):
        if type(pid) is not int or pid<=4:raise ValueError('Refusing a system or invalid PID')
        self.pid=pid;self.handle=K.OpenProcess(0x100000|0x1000|0x0001,False,pid)
        if not self.handle:
            err=c.get_last_error()
            if err==87:self.handle=None
            else:raise c.WinError(err)
    def running(self):
        if not self.handle:return False
        code=K.WaitForSingleObject(self.handle,0)
        if code==258:return True
        if code==0:return False
        raise c.WinError(c.get_last_error())
    def terminate_owned(self,expected,executable,digest):
        if not self.running():return False
        actual=handle_identity(self.handle,self.pid)
        if not identity_matches(expected,actual,executable,digest):raise RuntimeError('Owned-process identity mismatch; no process terminated')
        if not K.TerminateProcess(self.handle,1):raise c.WinError(c.get_last_error())
        code=K.WaitForSingleObject(self.handle,10000)
        if code!=0:raise RuntimeError('Owned process did not exit; keep reduced power limit')
        return True
    def close(self):
        if self.handle:K.CloseHandle(self.handle);self.handle=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
