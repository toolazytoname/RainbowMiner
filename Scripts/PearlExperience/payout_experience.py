# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""One-shot public-pool payout experience; no auto-restart, trading or wallet signing."""
import datetime,decimal,html,json,os,pathlib,subprocess,sys,threading,time,urllib.request
from pearl_controller import mining_mutex,Controller,EndSession,ROOT,RT,load,write,now
from payout_limits import resume_deadline,seconds_left
D=decimal.Decimal
BASE='https://pool.kryptex.com'
PUBLIC=urllib.request.build_opener(urllib.request.ProxyHandler({}))
STATUS=RT/'payout-experience.json'
REPORT=RT/'体验进度.html'
MAX_MINE_SECONDS=36*3600
MAX_WAIT_SECONDS=12*3600

def interpret(balance,payouts):
    def amount(key):
        value=D(str(balance[key]))
        if not value.is_finite() or value<0:raise ValueError('Invalid pool amount: '+key)
        return value
    total=amount('total');confirmed=amount('confirmed');pending=amount('unconfirmed');threshold=amount('threshold')
    if threshold<=0 or threshold>100000:raise ValueError('Invalid payout threshold')
    if abs(total-confirmed-pending)>D('0.0000001'):raise ValueError('Inconsistent pool balances')
    count=payouts['count']
    if type(count) is not int or count<0:raise ValueError('Invalid payout count')
    paid=count>0
    reached=paid or total>=threshold
    return {'TotalPrl':str(total),'ConfirmedPrl':str(confirmed),'UnconfirmedPrl':str(pending),'ThresholdPrl':str(threshold),'RemainingPrl':str(max(D(0),threshold-total)),'PayoutCount':count,'GoalReached':reached,'PayoutRecorded':paid,'MaturationEstimateSeconds':balance.get('maturation_time'),'Payouts':json.loads(json.dumps(payouts.get('results',[])[:3],default=str))}

def fetch(wallet):
    values=[]
    for endpoint in ['balance','payouts']:
        url=f'{BASE}/prl/api/v1/miner/{endpoint}/{wallet}'
        with PUBLIC.open(urllib.request.Request(url,headers={'User-Agent':'LazyPC-Pearl-Experience/1.0'}),timeout=8) as response:
            values.append(json.load(response,parse_float=D))
    return interpret(*values)

def render(state):
    phase={'preflight':'准备中','mining':'累计到门槛后自动停止','waiting_for_pool_payout':'挖矿已结束，等待矿池确认和打款','payout_recorded':'矿池已记录打款，体验结束','stopped_before_goal':'已停止，不自动重启','waiting_timeout':'挖矿已结束，打款尚待确认','error':'已停止，检查记录'}.get(state.get('Phase'),state.get('Phase',''))
    esc=lambda value:html.escape(str(value))
    cells=''.join(f'<tr><th>{label}</th><td>{esc(state.get(key,"—"))}</td></tr>' for key,label in [('Time','更新时间'),('TotalPrl','池内累计 PRL'),('ConfirmedPrl','已确认 PRL'),('UnconfirmedPrl','待确认 PRL'),('ThresholdPrl','打款门槛 PRL'),('RemainingPrl','距离门槛 PRL'),('PayoutCount','矿池打款记录数'),('MiningStopped','挖矿是否停止'),('PowerRestored','原功率限制已恢复'),('MiningDeadline','挖矿最长截止时间'),('SessionStopReason','停止原因'),('Error','最近错误')])
    url=BASE+'/prl/miner/stats/'+state['Wallet']
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="60"><title>Pearl 一次体验</title><style>body{{font:17px/1.7 system-ui,sans-serif;max-width:860px;margin:45px auto;padding:0 24px;background:#f6f7f9;color:#20252d}}table{{width:100%;border-collapse:collapse;background:white}}th,td{{text-align:left;padding:10px 15px;border-bottom:1px solid #e5e7eb}}th{{width:44%;font-weight:500}}a{{color:#2759c7}}</style><h1>Pearl 一次体验</h1><p>{esc(phase)}</p><p>池内累计（已确认＋待确认）达到打款门槛，或矿池出现打款记录，即停止显卡挖矿并恢复本轮开始前的功率限制。待确认收益继续由矿池处理，无需继续挖矿。</p><table>{cells}</table><p>温度保护、手动停止和 GPU 任务让路继续有效；停止后不会自动重启。最长挖矿 36 小时；矿池接口连续 30 分钟不可用则停止。</p><p><a href="{esc(url)}">打开自己的矿池页面</a>。打款记录不等于人民币提现；本轮直接收取 PRL，不做兑换。</p><p>只查询公开地址；程序不会读取助记词、私钥或钱包密码。</p></html>'
    REPORT.write_text(page,encoding='utf-8')

class Experience(Controller):
    def __init__(self):
        super().__init__('mine')
        self.end_reason=None;self.monitor_stop=threading.Event();self.monitor=None
        previous=load(STATUS) if STATUS.exists() else None
        if previous and previous.get('Wallet')!=self.cfg['wallet']:raise ValueError('Existing experience belongs to a different public wallet')
        current=datetime.datetime.now().astimezone()
        original_deadline=resume_deadline(previous,current)
        self.state={'Time':now(),'Phase':'preflight','Wallet':self.cfg['wallet'],'MiningStopped':False,'PowerRestored':False,'HardMiningHours':36,'NoAutomaticRestart':True,'MiningDeadline':original_deadline.isoformat(),'DeadlinePolicy':'Resume original deadline; no restart extension'}
        self.deadline=time.monotonic()+seconds_left(original_deadline,current)
    def publish(self):
        self.state['Time']=now();write(STATUS,self.state);render(self.state)
        if self.run:
            with (self.run/'pool-balance.ndjson').open('a',encoding='utf-8') as out:out.write(json.dumps(self.state,ensure_ascii=False)+'\n')
    def read_pool(self):
        snapshot=fetch(self.cfg['wallet']);self.state.update(snapshot,Error=None);self.publish();return snapshot
    def check_stop(self):
        super().check_stop()
        if self.end_reason:raise EndSession(self.end_reason)
        if time.monotonic()>=self.deadline:raise EndSession('original_mining_deadline_reached')
    def watch(self):
        last_ok=time.monotonic()
        while not self.monitor_stop.is_set():
            try:
                snapshot=self.read_pool();last_ok=time.monotonic()
                if snapshot['GoalReached']:
                    self.end_reason='first_pool_payout_recorded' if snapshot['PayoutRecorded'] else 'payout_threshold_accumulated'
                    return
            except Exception as exc:
                self.state['Error']=str(exc)
                if time.monotonic()-last_ok>=1800:self.end_reason='pool_api_unavailable_30_minutes'
                self.publish()
            if self.monitor_stop.wait(60):return
    def mine(self,watts,seconds,label,extend=False):
        if extend:raise ValueError('This experience does not run calibration')
        remaining=min(seconds,int(self.deadline-time.monotonic()))
        if remaining<=0:raise EndSession('original_mining_deadline_reached')
        self.state.update(Phase='mining',SessionId=self.s.get('SessionId'),RunDirectory=str(self.run));self.publish()
        self.monitor=threading.Thread(target=self.watch,name='public-pool-watch',daemon=True);self.monitor.start()
        try:return super().mine(watts,remaining,label,extend=False)
        finally:
            self.monitor_stop.set()
            if self.monitor:self.monitor.join(timeout=20)
    def execute(self):
        with mining_mutex('Global\\LazyPC-PearlPayoutExperience'):return self._execute_experience_locked()
    def _execute_experience_locked(self):
        try:
            with mining_mutex():
                first=self.read_pool()
                if first['GoalReached']:
                    self.state.update(MiningStopped=True,PowerRestored=True,Phase='payout_recorded' if first['PayoutRecorded'] else 'waiting_for_pool_payout');self.publish()
                else:
                    if self.deadline<=time.monotonic():
                        self.state.update(MiningStopped=True,PowerRestored=True,Phase='stopped_before_goal',SessionStopReason='original_mining_deadline_reached');self.publish();return
                    super()._execute_locked()
                    latest=load(RT/'session.json')
                    mine_result=None
                    result_file=self.run/'selected-profile'/'result.json' if self.run else None
                    if result_file and result_file.exists():mine_result=load(result_file)
                    self.state.update(MiningStopped=latest.get('Status')=='stopped',PowerRestored=latest.get('PowerRestored'),SessionStopReason=latest.get('StopReason'),ProfileStopReason=(mine_result or {}).get('StopReason'))
                    # A manual stop or thermal/resource guard ends the experience; never restart a miner.
                    self.state['Phase']='waiting_for_pool_payout' if self.state.get('GoalReached') else 'stopped_before_goal'
                    self.publish()
            if self.state['Phase']=='waiting_for_pool_payout':
                end=time.monotonic()+MAX_WAIT_SECONDS
                while time.monotonic()<end:
                    try:
                        snapshot=self.read_pool()
                        if snapshot['PayoutRecorded']:
                            self.state['Phase']='payout_recorded';self.publish();return
                    except Exception as exc:self.state['Error']=str(exc);self.publish()
                    time.sleep(300)
                self.state['Phase']='waiting_timeout';self.publish()
        except Exception as exc:
            self.state.update(Phase='error',Error=str(exc));self.publish();raise
        finally:
            self.monitor_stop.set()
            if self.monitor:self.monitor.join(timeout=20)
            if self.run:write(self.run/'experience-result.json',self.state)

def self_test():
    def b(total,confirmed='0',pending=None,threshold='1'):
        return {'total':total,'confirmed':confirmed,'unconfirmed':total if pending is None else pending,'threshold':threshold}
    empty={'count':0,'results':[]}
    assert not interpret(b('0.99999999'),empty)['GoalReached']
    assert interpret(b('1'),empty)['GoalReached']
    assert interpret(b('0'),{'count':1,'results':[{'txid':'test-only','amount':D('1.01')}]})['GoalReached']
    json.dumps(interpret(b('0'),{'count':1,'results':[{'amount':D('1.01')}]}))
    assert interpret(b('1.1','0.6','0.5'),empty)['RemainingPrl']=='0'
    assert not interpret(b('1',threshold='2'),empty)['GoalReached']
    for bad in [b('-1'),b('NaN'),b('1','0','0'),b('0',threshold='0')]:
        try:interpret(bad,empty)
        except ValueError:pass
        else:raise AssertionError('Invalid balance was accepted')
    print('SELF_TEST_OK: below/exact threshold, pending maturity, recorded payout, custom threshold and invalid API data')

if __name__=='__main__':
    if '--self-test' in sys.argv:self_test()
    elif '--check-pool' in sys.argv:print(json.dumps(fetch(load(ROOT/'mining-config.json')['wallet']),ensure_ascii=False))
    else:
        # Verify the public API before starting GPU work. Controller independently guards GPU/sensors.
        Experience().execute()
