# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Pinned compute backends and explicit reported-rate units; no GPU initialization."""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

class BackendStatsError(ValueError):pass

def number(value,*,integral=False):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (integral and int(value)!=value):
        raise BackendStatsError('Invalid backend rate/share number')
    return value

@dataclass(frozen=True)
class ComputeBackend:
    kind:str
    executable:Path
    sha256:str
    rate_unit:str
    shape:str=''
    tile:str=''
    def verify_binary(self):
        if not self.executable.is_file():raise ValueError('Configured backend executable is missing')
        with self.executable.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=self.sha256:raise ValueError('Configured backend executable hash changed')
    def command(self,endpoint,cfg):
        pool=urlsplit(endpoint)
        if pool.scheme!='stratum+tcp' or pool.hostname!='127.0.0.1' or not pool.port or pool.username or pool.password or pool.path or pool.query or pool.fragment:
            raise ValueError('Backend must use the owned loopback transport')
        if self.kind=='soat':
            return [str(self.executable),'--algo','pearl-pow','--device','0','--pool',f'127.0.0.1:{pool.port}','--wallet',cfg['wallet'],'--worker',cfg['worker'],'--plain','--interval','5']
        return [str(self.executable),'--coin','pearl','--url',endpoint,'--user',cfg['wallet']+'/'+cfg['worker'],'--devices-pci','01:00.0','--no-rocm','--no-intel','--api-host','127.0.0.1','--api-port','18490','--no-tui','--log-level','info']
    def environment(self):
        env=os.environ.copy()
        for key in ['SOAT_PEARL_SHAPE','SOAT_PEARL_TILE','SOAT_PEARL_PROFILE']:env.pop(key,None)
        if self.kind=='soat':env.update(SOAT_PEARL_SHAPE=self.shape,SOAT_PEARL_TILE=self.tile)
        return env
    def receipt(self):
        return dict(Kind=self.kind,Executable=str(self.executable),Sha256=self.sha256,ReportedRateUnit=self.rate_unit,Shape=self.shape,Tile=self.tile)

def select_compute_backend(cfg,root):
    kind=cfg.get('backend','krig')
    if kind=='soat':
        item=cfg.get('source_backend',{});exe=Path(item['executable']);digest=item['sha256'].lower()
        if not exe.is_absolute() or exe.name.lower()!='soat-miner.exe':raise ValueError('Expected absolute source backend executable path')
        if item.get('shape')!='4096x65536' or item.get('tile')!='=ampere large s3 fold k64':raise ValueError('Only the validated source shape/tile is enabled')
        unit='T MAC/s';shape=item['shape'];tile=item['tile']
    elif kind=='krig':
        if cfg.get('allow_krig_relay_fee') is not True:raise ValueError('KRig classifies the loopback relay as a third-party pool and charges 3%; select the validated source backend or explicitly configure that fee')
        exe=Path(root)/'1.5.12/krig-miner.exe';digest=cfg['exe_sha256'].lower();unit='TH/s';shape=tile=''
    else:raise ValueError('Unsupported compute backend; no CPU fallback')
    if not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Expected backend SHA-256')
    return ComputeBackend(kind,exe,digest,unit,shape,tile)

def read_source_stats(path):
    path=Path(path)
    try:
        with path.open('rb') as f:
            f.seek(0,2);size=f.tell();f.seek(max(0,size-65536));lines=f.read().decode('utf-8',errors='replace').splitlines()
        modified=path.stat().st_mtime
    except FileNotFoundError:return None
    for line in reversed(lines):
        try:row=json.loads(line)
        except ValueError:continue
        if not isinstance(row,dict) or 'rate' not in row:continue
        if row.get('algo')!='pearl-pow' or row.get('backend')!='CUDA' or row.get('unit')!='T MAC/s':raise BackendStatsError('Source backend must report CUDA T MAC/s; no unit conversion or CPU fallback')
        if time.time()-modified>30:raise BackendStatsError('Source telemetry is stale')
        rate=number(row['rate']);accepted=number(row.get('accepted'),integral=True);rejected=number(row.get('rejected'),integral=True);uptime=number(row.get('uptime_s'),integral=True)
        return dict(ReportedRate=rate,ReportedRateUnit='T MAC/s',AcceptedShares=accepted,RejectedShares=rejected,StaleShares=0,BackendUptimeSeconds=uptime,DeviceBackend='CUDA')
    return None
