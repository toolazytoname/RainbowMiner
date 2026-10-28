"""Fault-injection checks for payout bounds and hardware cleanup (no GPU)."""
import contextlib
import datetime as dt
import json
import pathlib
import tempfile
import time
import unittest
from unittest.mock import MagicMock, Mock, patch
import pearl_controller as pc
import payout_experience as pe
from payout_limits import resume_deadline, seconds_left

class BudgetTests(unittest.TestCase):
    def test_original_deadline_not_renewed(self):
        now=dt.datetime(2026,10,28,tzinfo=dt.timezone.utc)
        previous={"MiningDeadline":(now+dt.timedelta(hours=2)).isoformat()}
        self.assertEqual(seconds_left(resume_deadline(previous,now),now),7200)
        self.assertEqual(seconds_left(resume_deadline(previous,now+dt.timedelta(hours=3)),now+dt.timedelta(hours=3)),0)
    def test_timezone_required(self):
        now=dt.datetime.now(dt.timezone.utc)
        for previous in [{"MiningDeadline":"2026-10-28T12:00:00"},{"MiningDeadline":"invalid"}]:
            with self.assertRaises(ValueError):resume_deadline(previous,now)
        with self.assertRaises(ValueError):seconds_left(now,dt.datetime.now())
    def test_experience_reads_existing_deadline_and_wallet(self):
        with tempfile.TemporaryDirectory() as td:
            status=pathlib.Path(td)/"state.json"
            deadline=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat()
            status.write_text(json.dumps({"Wallet":"public-test","MiningDeadline":deadline}))
            def init(obj,*args):obj.cfg={"wallet":"public-test"};obj.run=None
            with patch.object(pc.Controller,"__init__",init),patch.object(pe,"STATUS",status):
                e=pe.Experience()
                self.assertEqual(dt.datetime.fromisoformat(e.state["MiningDeadline"]),dt.datetime.fromisoformat(deadline))
                status.write_text(json.dumps({"Wallet":"different","MiningDeadline":deadline}))
                with self.assertRaises(ValueError):pe.Experience()
    def test_expired_experience_never_starts_gpu(self):
        e=object.__new__(pe.Experience);e.deadline=time.monotonic()-1;e.state={};e.monitor_stop=Mock();e.monitor=None;e.run=None
        e.read_pool=Mock(return_value={"GoalReached":False});e.publish=Mock()
        with patch.object(pc.Controller,"_execute_locked") as start,patch.object(pe,"mining_mutex",return_value=contextlib.nullcontext()):
            e._execute_experience_locked();start.assert_not_called()
        self.assertEqual(e.state["SessionStopReason"],"original_mining_deadline_reached")
    def test_read_only_payout_wait_releases_gpu_mutex(self):
        e=object.__new__(pe.Experience);e.state={};e.monitor_stop=Mock();e.monitor=None;e.run=None;e.publish=Mock()
        held=[False];reads=[0]
        @contextlib.contextmanager
        def lock():
            held[0]=True
            try:yield
            finally:held[0]=False
        def pool():
            reads[0]+=1
            self.assertEqual(held[0],reads[0]==1)
            return {"GoalReached":True,"PayoutRecorded":reads[0]>1}
        e.read_pool=pool
        with patch.object(pe,"mining_mutex",lock),patch.object(pc.Controller,"check_stop"):e._execute_experience_locked()
        self.assertEqual(e.state["Phase"],"payout_recorded")
    def test_mine_respects_shorter_manual_duration(self):
        e=object.__new__(pe.Experience);e.mode='mine';e.monitor=None;e.deadline=time.monotonic()+3600;e.state={};e.s={};e.run=None;e.publish=Mock();e.monitor_stop=Mock()
        with patch.object(pe.threading,"Thread") as thread,patch.object(pc.Controller,"mine",return_value={}) as mine:
            e.mine(220,60,"test");self.assertEqual(mine.call_args.args[1],60)
            with self.assertRaises(ValueError):e.mine(220,60,"test",extend=True)
    def test_calibration_keeps_one_pool_watch_and_original_deadline(self):
        e=object.__new__(pe.Experience);e.mode='calibrate';e.monitor=None;e.deadline=time.monotonic()+30;e.state={};e.s={};e.run=None;e.publish=Mock();e.monitor_stop=Mock()
        with patch.object(pe.threading,"Thread") as thread,patch.object(pc.Controller,"mine",return_value={}) as mine:
            e.mine(180,720,"profile-180",extend=True);e.mine(200,720,"profile-200",extend=True)
            self.assertEqual(thread.call_count,1);e.monitor_stop.set.assert_not_called()
            self.assertTrue(all(0<c.args[1]<=30 and c.kwargs['extend'] for c in mine.call_args_list))
    def test_deadline_stops_during_calibration(self):
        e=object.__new__(pe.Experience);e.mode='calibrate';e.deadline=time.monotonic()-1;e.end_reason=None
        with patch.object(pc.Controller,"check_stop"):
            with self.assertRaisesRegex(pc.EndSession,"original_mining_deadline_reached"):e.check_stop()
    def test_pool_threshold_and_invalid_accounting(self):
        empty={"count":0,"results":[]}
        self.assertTrue(pe.interpret({"total":"1","confirmed":"0","unconfirmed":"1","threshold":"1"},empty)["GoalReached"])
        self.assertTrue(pe.interpret({"total":"0","confirmed":"0","unconfirmed":"0","threshold":"1"},{"count":1,"results":[]})["PayoutRecorded"])
        for total,pending,count in [("NaN","0",0),("1","0",0),("0","0",True)]:
            with self.assertRaises(ValueError):pe.interpret({"total":total,"confirmed":"0","unconfirmed":pending,"threshold":"1"},{"count":count,"results":[]})


class PayoutWaitTests(unittest.TestCase):
    def experience(self):
        e=object.__new__(pe.Experience)
        e.state={"Phase":"waiting_for_pool_payout","MiningStopped":True,"PowerRestored":True}
        e.end_reason="payout_threshold_accumulated";e.publish=Mock();e.read_pool=Mock()
        return e
    def test_manual_stop_before_poll_keeps_gpu_stopped(self):
        e=self.experience()
        with patch.object(pc.Controller,"check_stop",side_effect=pc.EndSession("user_stop")):
            e.wait_for_pool_payout()
        e.read_pool.assert_not_called()
        self.assertEqual(e.state["Phase"],"payout_wait_cancelled")
        self.assertEqual(e.state["PayoutWaitStopReason"],"user_stop")
        self.assertTrue(e.state["MiningStopped"] and e.state["PowerRestored"])
    def test_threshold_reason_does_not_cancel_read_only_settlement(self):
        e=self.experience();e.read_pool.return_value={"PayoutRecorded":True}
        with patch.object(pc.Controller,"check_stop") as manual_stop,patch.object(pe.Experience,"check_stop",side_effect=AssertionError("Mining checks cannot run after GPU release")):
            e.wait_for_pool_payout()
        manual_stop.assert_called_once_with(e)
        self.assertEqual(e.state["Phase"],"payout_recorded")
    def test_stop_interrupts_poll_gap_without_waiting_five_minutes(self):
        e=self.experience();e.read_pool.return_value={"PayoutRecorded":False}
        with patch.object(pc.Controller,"check_stop",side_effect=[None,pc.EndSession("user_stop")]),patch.object(pe.time,"sleep") as sleep:
            e.wait_for_pool_payout()
        sleep.assert_not_called();self.assertEqual(e.read_pool.call_count,1)
        self.assertEqual(e.state["Phase"],"payout_wait_cancelled")
    def test_api_error_can_still_be_cancelled(self):
        e=self.experience();e.read_pool.side_effect=TimeoutError("public API timeout")
        with patch.object(pc.Controller,"check_stop",side_effect=[None,pc.EndSession("user_stop")]),patch.object(pe.time,"sleep") as sleep:
            e.wait_for_pool_payout()
        sleep.assert_not_called();self.assertEqual(e.state["Error"],"public API timeout")
        self.assertEqual(e.state["Phase"],"payout_wait_cancelled")
    def test_read_only_wait_remains_bounded(self):
        e=self.experience()
        with patch.object(pe,"MAX_WAIT_SECONDS",0):e.wait_for_pool_payout()
        e.read_pool.assert_not_called();self.assertEqual(e.state["Phase"],"waiting_timeout")

class CleanupTests(unittest.TestCase):
    def controller(self,power=220):
        c=object.__new__(pc.Controller);c.s={"MiningPowerWatts":220,"MinerPid":123};c.proc=None;c.changed=True;c.original=370;c.gpu=Mock();c.save=Mock()
        state={"PowerLimit":power}
        c.gpu.read.side_effect=lambda:dict(state)
        c.gpu.power.side_effect=lambda watts:state.update(PowerLimit=watts)
        return c
    def test_stop_restores_original_cap(self):
        c=self.controller();c.stop_miner();c.gpu.power.assert_called_once_with(370)
        self.assertTrue(c.s["PowerRestored"]);self.assertFalse(c.changed)
    def test_external_cap_preserved(self):
        c=self.controller(200);c.stop_miner();c.gpu.power.assert_not_called()
        self.assertEqual(c.s["ExternalPowerChangePreserved"],200)
    def test_unstoppable_owned_child_keeps_cap_and_reference(self):
        c=self.controller();child=Mock();child.poll.return_value=None;child.wait.side_effect=TimeoutError();c.proc=child
        with self.assertRaises(RuntimeError):c.stop_miner()
        c.gpu.power.assert_not_called();self.assertIs(c.proc,child);self.assertTrue(c.changed)
    def test_session_finalizer_never_claims_stopped_for_live_child(self):
        c=self.controller();child=Mock();child.poll.return_value=None;child.wait.side_effect=TimeoutError();c.proc=child
        with tempfile.TemporaryDirectory() as td:
            c.run=pathlib.Path(td)
            with self.assertRaisesRegex(RuntimeError,'refusing a stopped status'):
                c.finalize_session('payout_threshold_accumulated')
            saved=json.loads((c.run/'session-result.json').read_text())
        c.gpu.power.assert_not_called();self.assertIs(c.proc,child);self.assertTrue(c.changed)
        self.assertEqual(saved['Status'],'stop-failed');self.assertTrue(saved['OwnedChildAlive'])
        self.assertEqual(saved['MinerPid'],123)
    def test_session_finalizer_records_stopped_only_after_cleanup(self):
        c=self.controller()
        with tempfile.TemporaryDirectory() as td:
            c.run=pathlib.Path(td);c.finalize_session('user_stop')
            saved=json.loads((c.run/'session-result.json').read_text())
        self.assertEqual(saved['Status'],'stopped');self.assertFalse(saved['OwnedChildAlive'])
        self.assertIsNone(saved['MinerPid']);self.assertTrue(saved['PowerRestored'])
        c.gpu.power.assert_called_once_with(370)
    def test_failed_tls_relay_stops_owned_miner_and_restores_cap(self):
        c=self.controller();c.mode='mine';c.cfg={'pool':'stratum+ssl://prl-hk.kryptex.network:8048','wallet':'public-test','worker':'test'}
        c.check_stop=Mock();c.guard=Mock()
        gpu={'PowerLimit':370,'Utilization':0,'MemoryMiB':0,'Temperature':40,'Hotspot':50,'MemoryJunction':50}
        c.gpu.read.side_effect=lambda:dict(gpu);c.gpu.power.side_effect=lambda watts:gpu.update(PowerLimit=watts)
        relay=MagicMock();relay.error=None;relay.thread.is_alive.return_value=False;relay.local_port=23456;relay.state={'upstream':'prl-hk.kryptex.network:8048'}
        child=Mock(pid=123);child.poll.return_value=None
        with tempfile.TemporaryDirectory() as td:
            c.run=pathlib.Path(td)
            with patch.object(pc,'verified_pool_transport',return_value=relay),patch.object(pc.subprocess,'Popen',return_value=child):
                with self.assertRaisesRegex(pc.EndSession,'verified_tls_relay_unavailable'):c.mine(220,60,'relay-fault')
        child.terminate.assert_called_once();relay.__exit__.assert_called_once()
        self.assertIsNone(c.proc);self.assertTrue(c.s['PowerRestored'])
        self.assertEqual([x.args[0] for x in c.gpu.power.call_args_list],[220,370])
    def test_missing_sensor_and_gpu_conflict_stop(self):
        c=self.controller();c.proc=Mock(pid=123)
        normal={"Temperature":70,"Hotspot":85,"MemoryJunction":80,"PowerLimit":220}
        with patch.object(pc,"gpu_processes",return_value={123:"krig-miner.exe",500:"blender.exe"}):
            with self.assertRaisesRegex(pc.GuardStop,"other_gpu_workload"):c.guard({"Gpu":normal},220)
        normal["Hotspot"]=float("nan")
        with self.assertRaisesRegex(pc.GuardStop,"invalid_temperature_sensor"):c.guard({"Gpu":normal},220)
    def test_gpu_application_during_cooldown_yields_before_any_mining(self):
        c=self.controller();c.telemetry=Mock(return_value={"Epoch":0,"Gpu":{"Temperature":40,"Hotspot":50,"MemoryJunction":50}})
        with patch.object(pc,"gpu_processes",return_value={999999:"blender.exe"}):
            with self.assertRaisesRegex(pc.EndSession,"other_gpu_workload_during_cooldown"):c.cooldown("test")
        c.gpu.power.assert_not_called()
    def test_runtime_preconditions_survive_optimized_python(self):
        c=self.controller()
        with self.assertRaises(ValueError):c.mine(280,60,"should-not-start")
        with self.assertRaises(ValueError):pc.require(False,"guard")

if __name__=="__main__":unittest.main(verbosity=2)
