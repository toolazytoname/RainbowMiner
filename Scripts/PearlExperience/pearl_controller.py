# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""User-authorized Pearl mining controller. No boot triggers, no CPU backend.
Stops and restores saved board power after user stop, time limit, sensor failure,
thermal protection, miner exit, or normal Python exception. Driver clocks/fans stay automatic.
"""
import contextlib,argparse,ctypes,datetime,hashlib,json,math,os,pathlib,statistics,subprocess,sys,time,urllib.request
from gpu_driver import Gpu
from pool_transport import verified_pool_transport
from compute_backend import select_compute_backend,read_source_stats,BackendStatsError
from process_identity import capture_owned_child,capture_controller
from gpu_clients import gpu_processes,DESKTOP_PROCESSES
SOURCE=pathlib.Path(__file__).parent;ROOT=pathlib.Path(os.environ.get('PRL_EXPERIENCE_HOME','D:/Apps/KRig')).resolve();RT=ROOT/'Runtime';EXE=ROOT/'1.5.12/krig-miner.exe'
PY=pathlib.Path(sys.executable);STOP=RT/'stop.request';CANCEL=RT/'cancel.request'
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def now():return datetime.datetime.now().astimezone().isoformat()
def write(path,data):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 for attempt in range(10):
  try:os.replace(tmp,path);return
  except PermissionError:
   if attempt==9:raise
   time.sleep(.1)
def require(condition,message):
 if not condition:raise ValueError(message)

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
@contextlib.contextmanager
def mining_mutex(name='Global\\LazyPC-PearlMining'):
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.CreateMutexW.restype=ctypes.c_void_p;kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p]
 kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.ReleaseMutex.argtypes=[ctypes.c_void_p]
 handle=kernel.CreateMutexW(None,False,name)
 if not handle:raise ctypes.WinError(ctypes.get_last_error())
 acquired=False
 try:
  acquired=kernel.WaitForSingleObject(handle,0) in [0,128]
  if not acquired:raise RuntimeError('Another mining session is already running')
  yield handle
 finally:
  if acquired:kernel.ReleaseMutex(handle)
  kernel.CloseHandle(handle)

class EndSession(Exception):pass
class GuardStop(Exception):pass
class Controller:
 def __init__(self,mode,resume_file=None):
  self.resume=pathlib.Path(resume_file) if resume_file else None
  self.cfg=load(ROOT/'mining-config.json');self.backend=select_compute_backend(self.cfg,ROOT);self.mode=mode;self.gpu=Gpu();self.proc=None;self.changed=False;self.mutex=None
  self.original=self.gpu.read()['PowerLimit'];self.s={};self.run=None;self.samples=[];self.last_api={}
 def save(self):write(RT/'session.json',self.s)
 def check_stop(self):
  if STOP.exists() or CANCEL.exists():raise EndSession('user_stop')
 def api(self):
  if self.backend.kind=='soat':
   try:
    value=read_source_stats(self.backend_log)
    if value:self.last_api=value
    return self.last_api
   except BackendStatsError as exc:raise GuardStop(str(exc))
  try:
   with OPENER.open('http://127.0.0.1:18490/',timeout=1) as r:d=json.load(r)
   a=d['devices'][0]['algorithms'][0]
   self.last_api={'ReportedRate':a['hashrate']/1e12,'ReportedRateUnit':'TH/s','HashrateTHs':a['hashrate']/1e12,'AcceptedShares':a['shares']['accepted'],'RejectedShares':a['shares']['rejected'],'StaleShares':a['shares']['stale']}
  except Exception:pass
  return self.last_api
 def telemetry(self,stage):
  self.check_stop();g=self.gpu.read();row={'Time':now(),'Epoch':time.time(),'Stage':stage,'Gpu':g,**(self.api() if self.proc else {})}
  with (self.run/'telemetry.ndjson').open('a',encoding='utf-8') as out:out.write(json.dumps(row,ensure_ascii=False)+'\n')
  self.s.update({'LastTelemetry':g,'ReportedRate':round(row.get('ReportedRate',0),2),'ReportedRateUnit':self.backend.rate_unit,'AcceptedShares':row.get('AcceptedShares',0),'RejectedShares':row.get('RejectedShares',0),'StaleShares':row.get('StaleShares',0),'LastUpdate':row['Time'],'BackendUptimeSeconds':row.get('BackendUptimeSeconds')})
  if self.backend.kind=='krig':self.s['HashrateTHs']=self.s['ReportedRate']
  else:self.s.pop('HashrateTHs',None)
  self.save()
  return row
 def guard(self,row,watts):
  g=row['Gpu']
  for name,key in [('core_temperature_guard','Temperature'),('hotspot_temperature_guard','Hotspot'),('memory_temperature_guard','MemoryJunction')]:
   limit={'Temperature':80,'Hotspot':100,'MemoryJunction':96}[key]
   if not isinstance(g.get(key),(int,float)) or not math.isfinite(g[key]):raise GuardStop('invalid_temperature_sensor_'+key)
   if g[key]>=limit:raise GuardStop(name)
  if not math.isfinite(g['PowerLimit']) or abs(g['PowerLimit']-watts)>2:raise GuardStop('external_power_limit_change')
  allowed={os.getpid(),self.proc.pid if self.proc else None}
  if any(pid not in allowed and name not in DESKTOP_PROCESSES for pid,name in gpu_processes().items()):raise GuardStop('other_gpu_workload')
 def stop_miner(self):
  if not self.s:return
  alive=False
  if self.proc:
   try:
    if self.proc.poll() is None:self.proc.terminate();self.proc.wait(timeout=10)
   except Exception:alive=self.proc.poll() is None
  if alive:raise RuntimeError('Miner failed to stop; retaining reduced power limit')
  self.proc=None
  if self.changed:
   current=self.gpu.read()['PowerLimit']
   if abs(current-self.s.get('MiningPowerWatts',current))<2:
    self.gpu.power(self.original);self.s['PowerRestored']=True
   elif abs(current-self.original)<2:self.s['PowerRestored']=True
   else:self.s['PowerRestored']=False;self.s['ExternalPowerChangePreserved']=current
   self.changed=False
  self.s['MinerPid']=None;self.s['LastTelemetry']=self.gpu.read();self.s['PowerRestored']=abs(self.s['LastTelemetry']['PowerLimit']-self.original)<2;self.save()
 def finalize_session(self,reason):
  try:self.stop_miner()
  except Exception as exc:reason+='; restore_error: '+str(exc)
  alive=self.proc is not None and self.proc.poll() is None
  if self.s:
   self.s.update(Status='stop-failed' if alive else 'stopped',StopReason=reason,OwnedChildAlive=alive,EndTime=now());self.save();write(self.run/'session-result.json',self.s)
  else:write(RT/'last-start-error.json',{'Time':now(),'Reason':reason})
  if alive:raise RuntimeError('Owned miner is still alive; retaining reduced cap and refusing a stopped status')
 def cooldown(self,label):
  self.s.update(Status='cooling',Phase=label,ReportedRate=0,ReportedRateUnit=self.backend.rate_unit,MiningPowerWatts=0,CooldownReason='至少3分钟；核心≤50℃、热点≤65℃、显存≤65℃，最后1分钟温度波动≤2℃');self.save()
  start=time.monotonic();rows=[]
  while time.monotonic()-start<900:
   row=self.telemetry('cooldown');rows.append(row);tail=[x for x in rows if row['Epoch']-x['Epoch']<=60]
   if any(pid!=os.getpid() and name not in DESKTOP_PROCESSES for pid,name in gpu_processes().items()):raise EndSession('other_gpu_workload_during_cooldown')
   g=row['Gpu'];ready=g['Temperature']<=50 and g['Hotspot']<=65 and g['MemoryJunction']<=65
   stable=len(tail)>=10 and max(x['Gpu']['Temperature'] for x in tail)-min(x['Gpu']['Temperature'] for x in tail)<=2 and max(x['Gpu']['MemoryJunction'] for x in tail)-min(x['Gpu']['MemoryJunction'] for x in tail)<=2
   if time.monotonic()-start>=180 and ready and stable:
    return {'Seconds':round(time.monotonic()-start),'End':g,'WindowSeconds':60,'TemperatureRange':max(x['Gpu']['Temperature'] for x in tail)-min(x['Gpu']['Temperature'] for x in tail)}
   time.sleep(5)
  raise EndSession('cooldown_not_ready_within_15_minutes')
 def steady(self,rows):
  tail=[r for r in rows if rows[-1]['Epoch']-r['Epoch']<=180]
  if len(tail)<20:return False
  n=max(1,len(tail)//3)
  return all(abs(statistics.mean(r['Gpu'][key] for r in tail[-n:])-statistics.mean(r['Gpu'][key] for r in tail[:n]))<=1 for key in ['Temperature','MemoryJunction','Hotspot'])
 def mine(self,watts,seconds,label,extend=False):
  require(isinstance(watts,int) and not isinstance(watts,bool) and 100<=watts<=220,'Power outside the conservative 100..220 W operating range')
  require(isinstance(seconds,(int,float)) and math.isfinite(seconds) and seconds>0,'Mining time must be finite and positive')
  self.check_stop();g=self.gpu.read()
  if g['Utilization']>15 or g['MemoryMiB']>2500:raise EndSession('other_gpu_workload_before_start')
  self.guard({'Gpu':g},g['PowerLimit'])
  self.samples=[];self.last_api={};start=time.monotonic();reason='time_limit';sub=self.run/label;sub.mkdir(exist_ok=True)
  self.s.update(Status='calibrating' if extend else 'running',Phase=label,MiningPowerWatts=watts,PowerRestored=False,ReportedRate=0,ReportedRateUnit=self.backend.rate_unit,AcceptedShares=0,RejectedShares=0,PlannedStop=(datetime.datetime.now().astimezone()+datetime.timedelta(seconds=seconds+(360 if extend else 0))).isoformat())
  self.save();self.changed=True;self.gpu.power(watts)
  log=(sub/'miner.log').open('wb');err=(sub/'miner-error.log').open('wb');relay=None
  try:
   relay=verified_pool_transport(self.cfg['pool'],sub/'tls-status.json');relay.__enter__()
   endpoint='stratum+tcp://127.0.0.1:'+str(relay.local_port)
   self.s['VerifiedTlsRelay']={'Upstream':relay.state['upstream'],'ClientEndpoint':endpoint,'Receipt':str(sub/'tls-status.json'),'ControllerPid':os.getpid(),'CertificateRequired':True,'HostnameRequired':True};self.save()
   args=self.backend.command(endpoint,self.cfg);self.backend_log=sub/'miner.log'
   self.proc=subprocess.Popen(args,cwd=self.backend.executable.parent,env=self.backend.environment(),stdout=log,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   self.s['MinerPid']=self.proc.pid;self.s['MinerIdentity']=capture_owned_child(self.proc);self.save()
   while True:
    if relay.error or not relay.thread.is_alive():raise GuardStop('verified_tls_relay_unavailable')
    if self.proc.poll() is not None:raise GuardStop('miner_exited')
    row=self.telemetry(label);self.samples.append(row);self.guard(row,watts)
    if self.backend.kind=='soat' and time.monotonic()-start>90 and not self.last_api:raise GuardStop('source_telemetry_unavailable')
    elapsed=time.monotonic()-start
    if elapsed>=seconds:
     if not extend or self.steady(self.samples) or elapsed>=seconds+360:break
    time.sleep(5)
  except GuardStop as e:reason=str(e)
  finally:
   try:self.stop_miner()
   finally:
    try:
     if relay:relay.__exit__()
    finally:log.close();err.close()
  end=self.samples[-1]['Epoch'] if self.samples else 0
  tail=[r for r in self.samples if end-r['Epoch']<=180 and r.get('ReportedRate',r.get('HashrateTHs',0))>0]
  if not tail:raise EndSession(reason if reason!='time_limit' else 'No valid mining hashrate samples')
  mean=lambda key:round(statistics.mean(r['Gpu'][key] for r in tail),2)
  rate=round(statistics.mean(r['ReportedRate'] for r in tail),2);power=mean('Power')
  result={'PowerLimitWatts':watts,'Seconds':round(time.monotonic()-start),'StopReason':reason,'Steady':self.steady(self.samples),'BackendKind':self.backend.kind,'ReportedRateUnit':self.backend.rate_unit,'AverageReportedRate':rate,'AverageGpuWatts':power,'ReportedRatePerWatt':round(rate/power,5),'CoreAverage':mean('Temperature'),'CoreMaximum':max(r['Gpu']['Temperature'] for r in self.samples),'CoreSteadyMaximum':max(r['Gpu']['Temperature'] for r in tail),'HotspotAverage':mean('Hotspot'),'HotspotMaximum':max(r['Gpu']['Hotspot'] for r in self.samples),'MemoryJunctionAverage':mean('MemoryJunction'),'MemoryJunctionMaximum':max(r['Gpu']['MemoryJunction'] for r in self.samples),'FanPercentAverage':mean('FanPercent'),'AcceptedShares':self.samples[-1].get('AcceptedShares',0),'RejectedShares':self.samples[-1].get('RejectedShares',0),'Samples':len(self.samples),'StableWindowSeconds':180,'RunDirectory':str(sub)}
  if self.backend.kind=='krig':result.update(AverageHashrateTHs=rate,THsPerWatt=round(rate/power,5))
  write(sub/'result.json',result);return result
 def execute(self):
  with mining_mutex():return self._execute_locked()
 def _execute_locked(self):
  reason='completed'
  try:
   self.backend.verify_binary()
   for p in [STOP,CANCEL]:p.unlink(missing_ok=True)
   g=self.gpu.read();self.original=g['PowerLimit']
   if g['Utilization']>15 or g['MemoryMiB']>2500:raise RuntimeError('GPU is busy; refusing to interrupt another workload')
   if any(pid!=os.getpid() and name not in DESKTOP_PROCESSES for pid,name in gpu_processes().items()):raise RuntimeError('Another GPU application is present; refusing to start')
   completed=[]
   if self.resume:
    require(self.mode=='calibrate' and self.resume.name=='calibration-progress.json','Invalid resume file')
    require(self.resume.parent.parent.resolve()==(pathlib.Path('D:/AI/Playgrounds')/('RainbowMiner' if self.backend.kind=='soat' else 'KRig')).resolve(),'Resume path is outside our run directory')
    record=load(self.resume);require(record.get('BackendKind','krig')==self.backend.kind,'Cannot mix compute backends in a calibration resume');require(record.get('Status')=='running','Calibration is already complete')
    completed=record['Results'];require(completed and [r['PowerLimitWatts'] for r in completed] in [[180],[180,200]],'Unexpected completed profiles')
    require(all(r['StopReason']=='time_limit' and r['Steady'] for r in completed),'Cannot resume above a failed profile')
    self.run=self.resume.parent;previous=load(RT/'session.json')
    require(previous['Status']=='stopped' and pathlib.Path(previous['RunDirectory']).resolve()==self.run.resolve(),'Previous session is not stopped')
    write(self.run/('previous-controller-'+str(previous['ControllerPid'])+'.json'),previous)
   else:
    self.run=pathlib.Path('D:/AI/Playgrounds')/('RainbowMiner' if self.backend.kind=='soat' else 'KRig')/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+self.backend.kind+'-'+self.mode);self.run.mkdir(parents=True)
   self.s={'SessionId':self.run.name,'Status':'starting','Mode':self.mode,'ControllerPid':os.getpid(),'MinerPid':None,'StartTime':now(),'OriginalPowerWatts':self.original,'MiningPowerWatts':0,'PowerRestored':False,'RunDirectory':str(self.run),'Wallet':self.cfg['wallet'],'Worker':self.cfg['worker'],'Pool':self.cfg['pool'],'LastTelemetry':g,'StopReason':None,'ThermalGuards':{'Core':80,'Hotspot':100,'MemoryJunction':96},'ClocksAndFans':'driver automatic; unchanged','SecuritySettingsChanged':False}
   self.s['ControllerIdentity']=capture_controller();self.s['ComputeBackend']=self.backend.receipt();self.s['ReportedRate']=0;self.s['ReportedRateUnit']=self.backend.rate_unit
   self.s['ManagementSourceDirectory']=str(SOURCE)
   self.s['ManagementSourceSha256']={}
   for filename in ['pearl_controller.py','payout_experience.py','gpu_clients.py','gpu_driver.py','payout_limits.py','pool_transport.py','tls_relay.py','compute_backend.py','process_identity.py','recover_session.py','coexist_monitor.py']:
    with (SOURCE/filename).open('rb') as code:self.s['ManagementSourceSha256'][filename]=hashlib.file_digest(code,'sha256').hexdigest()
   self.save()
   subprocess.Popen([str(PY),str(SOURCE/'coexist_monitor.py')],cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
   if self.mode=='calibrate':
    results=list(completed)
    for watts in [180,200,220]:
     if any(r['PowerLimitWatts']==watts for r in completed):continue
     baseline=self.cooldown('准备'+str(watts)+'W')
     r=self.mine(watts,720,'profile-'+str(watts)+'W',extend=True);r['Cooldown']=baseline;results.append(r)
     write(self.run/'calibration-progress.json',{'Status':'running','BackendKind':self.backend.kind,'ReportedRateUnit':self.backend.rate_unit,'Results':results})
     if r['StopReason']!='time_limit':raise EndSession(r['StopReason'])
    eligible=[r for r in results if r['Steady'] and r['StopReason']=='time_limit' and r['CoreSteadyMaximum']<=78 and r['HotspotMaximum']<=95 and r['MemoryJunctionMaximum']<=90 and r['AcceptedShares']>0 and r['RejectedShares']==0]
    if not eligible:raise EndSession('No tested profile passed comfort criteria')
    best=max(r.get('ReportedRatePerWatt',r.get('THsPerWatt',0)) for r in eligible);choice=max((r for r in eligible if r.get('ReportedRatePerWatt',r.get('THsPerWatt',0))>=best*.95),key=lambda r:r.get('AverageReportedRate',r.get('AverageHashrateTHs',0)))
    self.cfg['power_watts']=choice['PowerLimitWatts'];write(ROOT/'mining-config.json',self.cfg)
    result={'Status':'complete','Time':now(),'Results':results,'Selected':choice,'SelectionRule':'核心≤78℃，热点≤95℃，显存≤90℃，稳态且份额被接受；在最佳GPU能效95%以内选较快档位','LongRunMinutes':self.cfg.get('default_minutes',480),'OriginalPowerWatts':self.original,'Scope':'Only board power varied. Same miner, auto clocks/fans. GPU power only; whole-PC wall power not measured.'}
    write(self.run/'calibration-result.json',result);write(RT/'calibration-result.json',result)
    write(self.run/'calibration-progress.json',{'Status':'complete','BackendKind':self.backend.kind,'ReportedRateUnit':self.backend.rate_unit,'Results':results})
    self.cooldown('开始选定档位前冷却')
   else:
    g=self.gpu.read()
    if g['Temperature']>55 or g['MemoryJunction']>70:self.cooldown('开始前冷却')
   result=self.mine(int(self.cfg['power_watts']),int(self.cfg.get('default_minutes',480))*60,'selected-profile',extend=False)
   if result['StopReason']!='time_limit':raise EndSession(result['StopReason'])
  except (EndSession,GuardStop) as e:reason=str(e)
  except Exception as e:reason='error: '+str(e)
  finally:self.finalize_session(reason)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['run','check']);p.add_argument('--mode',choices=['mine','calibrate'],default='mine');p.add_argument('--resume-calibration');a=p.parse_args()
 if a.action=='check':print(json.dumps({'Driver':Gpu().read(),'Config':{k:v for k,v in load(ROOT/'mining-config.json').items() if k not in ['wallet','exe_sha256']}}))
 else:Controller(a.mode,a.resume_calibration).execute()
