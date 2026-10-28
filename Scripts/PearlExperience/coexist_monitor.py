# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Coexistence monitor: CPU jobs have priority; only stop our own miner on GPU conflict."""
import ctypes as c,datetime,json,os,pathlib,subprocess,time
from gpu_clients import gpu_processes,DESKTOP_PROCESSES
ROOT=pathlib.Path(os.environ.get('PRL_EXPERIENCE_HOME','D:/Apps/KRig')).resolve();RT=ROOT/'Runtime';K=c.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.restype=c.c_void_p;K.OpenProcess.argtypes=[c.c_uint,c.c_int,c.c_uint]
K.CloseHandle.argtypes=[c.c_void_p];K.SetPriorityClass.argtypes=[c.c_void_p,c.c_uint]
K.QueryFullProcessImageNameW.argtypes=[c.c_void_p,c.c_uint,c.c_wchar_p,c.POINTER(c.c_uint)]
class Mem(c.Structure):
 _fields_=[('length',c.c_uint),('load',c.c_uint)]+[(x,c.c_ulonglong) for x in ['total','available','pageTotal','pageAvailable','virtualTotal','virtualAvailable','extendedAvailable']]
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,obj):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(t,path)
def ticks():
 a=c.c_ulonglong();b=c.c_ulonglong();d=c.c_ulonglong()
 if not K.GetSystemTimes(c.byref(a),c.byref(b),c.byref(d)):raise c.WinError(c.get_last_error())
 return a.value,b.value+d.value
def priority(pid,expected):
 if not pid:return False
 h=K.OpenProcess(0x1200,False,int(pid))
 if not h:return False
 try:
  n=c.c_uint(32768);buf=c.create_unicode_buffer(n.value)
  if not K.QueryFullProcessImageNameW(h,0,buf,c.byref(n)):return False
  if pathlib.Path(buf.value).name.lower()!=expected:return False
  return bool(K.SetPriorityClass(h,0x4000))
 finally:K.CloseHandle(h)
def clients():
 return gpu_processes()
K.CreateMutexW.restype=c.c_void_p;K.CreateMutexW.argtypes=[c.c_void_p,c.c_int,c.c_wchar_p];K.WaitForSingleObject.argtypes=[c.c_void_p,c.c_uint];K.ReleaseMutex.argtypes=[c.c_void_p]
mutex=K.CreateMutexW(None,False,'Global\\LazyPC-PearlCoexist')
if K.WaitForSingleObject(mutex,10000) not in [0,128]:raise SystemExit(0)
try:
 s=read(RT/'session.json');sid=s['SessionId'];run=pathlib.Path(s['RunDirectory']);prev=ticks();initial=clients();miner=None;baseline=None;pressure=0;coolbusy=0;lastcoolstamp=None;cached=initial;cycle=0
 while True:
  time.sleep(5);s=read(RT/'session.json')
  if s['Status']=='stopped':break
  if s['SessionId']!=sid:
   sid=s['SessionId'];run=pathlib.Path(s['RunDirectory']);prev=ticks();initial=clients();miner=None;baseline=None;pressure=0;coolbusy=0;lastcoolstamp=None;cached=initial;cycle=0
  cp=priority(s.get('ControllerPid'),'python.exe');mp=priority(s.get('MinerPid'),'krig-miner.exe')
  idle,total=ticks();di=idle-prev[0];dt=total-prev[1];prev=(idle,total);cpu=round(100*(1-di/dt),1) if dt else 0
  mem=Mem();mem.length=c.sizeof(mem);K.GlobalMemoryStatusEx(c.byref(mem))
  g=s.get('LastTelemetry',{});pid=s.get('MinerPid');reason=None
  if pid!=miner:miner=pid;baseline=None;pressure=0
  if s.get('LastUpdate')!=lastcoolstamp:
   coolbusy=coolbusy+1 if not pid and s['Status']=='cooling' and g.get('MemoryMiB',0)>2500 else 0
   lastcoolstamp=s.get('LastUpdate')
  if coolbusy>=2:reason='other_gpu_workload_during_cooldown'
  if not cp:
   reason='controller_not_available';subprocess.run(['schtasks.exe','/Run','/TN','LazyPC-PearlMining-Recover'],capture_output=True,creationflags=0x08000000)
  if pid and g.get('MemoryMiB',0)>3000:
   if baseline is None:baseline=g['MemoryMiB']
   excess=g['MemoryMiB']-baseline;pressure=pressure+1 if excess>1536 else 0
   if pressure>=3 or g['MemoryMiB']>8500:reason='additional_gpu_memory_workload'
  if pid:
   if cycle%3==0:cached=clients()
   for other,name in cached.items():
    if other in [pid,s.get('ControllerPid')] or name in DESKTOP_PROCESSES:continue
    reason='other_gpu_workload';break
  row={'Time':datetime.datetime.now().astimezone().isoformat(),'SessionId':sid,'Phase':s.get('Phase'),'CpuPercent':cpu,'RamUsedGiB':round((mem.total-mem.available)/2**30,2),'RamAvailableGiB':round(mem.available/2**30,2),'ControllerBelowNormal':cp,'MinerBelowNormal':mp if pid else None,'MinerPid':pid,'GpuMemoryBaselineMiB':baseline,'GpuMemoryMiB':g.get('MemoryMiB'),'GpuYieldReason':reason,'Policy':'CPU workload never triggers a mining stop; our processes are BelowNormal. GPU pressure yields by stopping only our miner.'}
  with (run/'coexist.ndjson').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
  write(RT/'coexist-status.json',row)
  if reason:
   write(run/'gpu-yield.json',row);(RT/'stop.request').touch();(RT/'cancel.request').touch();break
  cycle+=1
except Exception as e:
 write(RT/'coexist-error.json',{'Time':datetime.datetime.now().astimezone().isoformat(),'Error':str(e)})
finally:K.ReleaseMutex(mutex);K.CloseHandle(mutex)
