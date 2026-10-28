"""Fault-injection checks for payout bounds and hardware cleanup (no GPU)."""
import contextlib
import datetime as dt
import json
import pathlib
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
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
        with patch.object(pe,"mining_mutex",lock):e._execute_experience_locked()
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
