# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit one-shot recovery: stop files, exact owned handles, then power."""
import argparse
import contextlib
import math
from pathlib import Path
import time
from pearl_controller import RT,load,write,now,mining_mutex
from process_identity import ProcessHandle
from gpu_driver import Gpu

def power_action(current,original,mining,worker_alive=False,controller_alive=False):
    if worker_alive or controller_alive:raise RuntimeError('Owned work has not exited; retaining reduced power')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in [current,original,mining]):raise ValueError('Invalid power recovery reading')
    if abs(current-original)<2:return 'already-restored'
    if abs(current-mining)<2:return 'restore-original'
    return 'preserve-external'

def same_session(sid):
    value=load(RT/'session.json')
    if value['SessionId']!=sid:raise RuntimeError('Session changed during recovery; no new session will be touched')
    return value

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check-only',action='store_true');a=ap.parse_args()
    initial=load(RT/'session.json');sid=initial['SessionId'];result={'Time':now(),'SessionId':sid,'Status':'requested','Restored':False,'ProcessesTerminated':[]}
    if a.check_only:
        print({'SessionId':sid,'Status':initial.get('Status'),'Policy':'Exact creation-time/image/hash before owned termination; no GPU/power/process changes in this check'});return 0
    for name in ['cancel.request','stop.request']:(RT/name).touch()
    worker=None;controller=None
    try:
        if initial.get('MinerPid'):worker=ProcessHandle(int(initial['MinerPid']))
        if initial.get('ControllerIdentity') and initial.get('Status')!='stopped':controller=ProcessHandle(int(initial['ControllerPid']))
        end=time.monotonic()+30
        while time.monotonic()<end:
            current=same_session(sid)
            if current.get('Status')=='stopped' and current.get('MinerPid') is None and (worker is None or not worker.running()):break
            time.sleep(.5)
        current=same_session(sid)
        if worker is not None and worker.running():
            backend=initial.get('ComputeBackend') or {}
            identity=initial.get('MinerIdentity') or {}
            if int(identity.get('ParentPid',0))!=int(initial['ControllerPid']):raise RuntimeError('Missing owned worker parent identity; retaining reduced cap')
            if worker.terminate_owned(identity,backend.get('Executable',''),backend.get('Sha256','')):result['ProcessesTerminated'].append('owned-miner')
        # Allow normal finally/TLS cleanup before considering the exact controller.
        end=time.monotonic()+20
        while time.monotonic()<end:
            current=same_session(sid)
            if controller is None or not controller.running():break
            time.sleep(.5)
        if controller is not None and controller.running():
            # Normal mining has ended; read-only payout waiting is also cancelled
            # by this explicit Stop. Only this captured controller can be ended.
            identity=initial['ControllerIdentity']
            if controller.terminate_owned(identity,identity['Executable'],identity['Sha256']):result['ProcessesTerminated'].append('owned-controller')
        if worker is not None and worker.running():raise RuntimeError('Owned worker still alive; power is not restored')
        if controller is not None and controller.running():raise RuntimeError('Owned controller still alive; power is not restored')
        current=same_session(sid)
        # A newer guarded experiment must never have its cap overwritten.
        with mining_mutex():
            current=same_session(sid);gpu=Gpu();before=gpu.read()['PowerLimit']
            action=power_action(before,float(initial['OriginalPowerWatts']),float(initial.get('MiningPowerWatts') or before))
            if action=='restore-original':gpu.power(float(initial['OriginalPowerWatts']))
            actual=gpu.read()['PowerLimit'];restored=abs(actual-float(initial['OriginalPowerWatts']))<2
            result.update(Status='stopped',PowerAction=action,ActualPowerLimit=actual,ExpectedOriginalLimit=initial['OriginalPowerWatts'],Restored=restored)
            if current.get('Status')!='stopped':
                current.update(Status='stopped',StopReason='manual_recovery',MinerPid=None,OwnedChildAlive=False,PowerRestored=restored,EndTime=now(),ReportedRate=0)
                if current.get('LastTelemetry'):current['LastTelemetry']['PowerLimit']=actual
                write(RT/'session.json',current)
            payout=load(RT/'payout-experience.json')
            if payout.get('SessionId')==sid and payout.get('Phase') in ['mining','calibrating','waiting_for_pool_payout']:
                payout.update(MiningStopped=True,PowerRestored=restored,ManualRecoveryTime=now(),Phase='payout_wait_cancelled' if payout.get('GoalReached') else 'stopped_before_goal',PayoutWaitStopReason='user_stop');write(RT/'payout-experience.json',payout)
        return 0
    except Exception as exc:
        result.update(Status='recovery-error',Error=str(exc));raise
    finally:
        if worker:worker.close()
        if controller:controller.close()
        result['Time']=now();write(RT/'manual-stop-result.json',result)

if __name__=='__main__':raise SystemExit(main())
