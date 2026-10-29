"""Host-only startup load scenarios; no GPU process or power change."""
import unittest
from gpu_clients import gpu_busy_before_start
class PreflightTests(unittest.TestCase):
    def sample(self,**changes):
        data=dict(Utilization=34,MemoryMiB=1091,Power=17.9,CoreClockMHz=225,MemoryClockMHz=405)
        data.update(changes);return data
    def test_observed_idle_desktop_percentage_is_not_a_compute_load(self):
        self.assertFalse(gpu_busy_before_start(self.sample()))
    def test_high_power_gpu_work_is_refused(self):
        self.assertTrue(gpu_busy_before_start(self.sample(Power=180,CoreClockMHz=1500,MemoryClockMHz=9501)))
    def test_low_power_alone_does_not_excuse_active_clocks(self):
        self.assertTrue(gpu_busy_before_start(self.sample(CoreClockMHz=900,MemoryClockMHz=9501)))
    def test_normal_low_utilization_keeps_existing_behavior(self):
        self.assertFalse(gpu_busy_before_start(self.sample(Utilization=2,CoreClockMHz=1000,MemoryClockMHz=9501)))
    def test_existing_memory_limits_are_preserved(self):
        self.assertTrue(gpu_busy_before_start(self.sample(Utilization=0,MemoryMiB=3000)))
        self.assertTrue(gpu_busy_before_start(self.sample(Utilization=0,MemoryMiB=2200),memory_limit=2048))
    def test_source_stricter_utilization_threshold_is_preserved(self):
        data=self.sample(Utilization=12,Power=100,CoreClockMHz=1000,MemoryClockMHz=9501)
        self.assertFalse(gpu_busy_before_start(data))
        self.assertTrue(gpu_busy_before_start(data,utilization_limit=10,memory_limit=2048))
    def test_missing_or_invalid_busy_state_fails_closed(self):
        for key in ("Power","CoreClockMHz","MemoryClockMHz"):
            data=self.sample();data.pop(key)
            with self.subTest(key=key):self.assertTrue(gpu_busy_before_start(data))
        for key in ("Utilization","MemoryMiB","Power","CoreClockMHz","MemoryClockMHz"):
            for value in (float("nan"),-1,True):
                with self.subTest(key=key,value=value):self.assertTrue(gpu_busy_before_start(self.sample(**{key:value})))
    def test_high_percentage_with_only_part_of_idle_conditions_is_refused(self):
        for change in (dict(Power=60),dict(CoreClockMHz=800),dict(MemoryClockMHz=9501)):
            with self.subTest(change=change):self.assertTrue(gpu_busy_before_start(self.sample(**change)))
class StartupWaitTests(unittest.TestCase):
    def controller(self, readings):
        from unittest.mock import Mock
        from pearl_controller import Controller
        controller=object.__new__(Controller)
        controller.proc=None
        controller.gpu=Mock()
        controller.gpu.read.side_effect=readings
        controller.check_stop=Mock()
        return controller
    def reading(self, **changes):
        data=dict(Utilization=37,MemoryMiB=1113,Power=19.96,CoreClockMHz=450,
                  MemoryClockMHz=810,PowerLimit=370,Temperature=40,
                  Hotspot=50,MemoryJunction=44)
        data.update(changes)
        return data
    def test_transient_busy_waits_before_returning_idle_sample(self):
        from unittest.mock import patch
        c=self.controller([self.reading(),self.reading(CoreClockMHz=240)])
        with patch("pearl_controller.gpu_processes",return_value={}),patch("pearl_controller.time.sleep") as sleep:
            self.assertEqual(c.idle_before_start()["CoreClockMHz"],240)
        sleep.assert_called_once_with(1)
        c.gpu.power.assert_not_called()
    def test_persistent_busy_times_out_without_launch_or_power_change(self):
        from unittest.mock import patch
        from pearl_controller import EndSession
        c=self.controller([self.reading()])
        with patch("pearl_controller.gpu_processes",return_value={}),patch("pearl_controller.time.monotonic",side_effect=[0,31]):
            with self.assertRaisesRegex(EndSession,"other_gpu_workload_before_start"):c.idle_before_start()
        c.gpu.power.assert_not_called()
    def test_manual_stop_is_honored_while_waiting(self):
        from unittest.mock import patch
        from pearl_controller import EndSession
        c=self.controller([self.reading()])
        c.check_stop.side_effect=[None,EndSession("user_stop")]
        with patch("pearl_controller.gpu_processes",return_value={}),patch("pearl_controller.time.sleep"):
            with self.assertRaisesRegex(EndSession,"user_stop"):c.idle_before_start()
        c.gpu.power.assert_not_called()
    def test_other_gpu_application_is_refused_without_wait(self):
        from unittest.mock import patch
        from pearl_controller import GuardStop
        c=self.controller([self.reading(CoreClockMHz=240)])
        with patch("pearl_controller.gpu_processes",return_value={99999:"blender.exe"}),patch("pearl_controller.time.sleep") as sleep:
            with self.assertRaisesRegex(GuardStop,"other_gpu_workload"):c.idle_before_start()
        sleep.assert_not_called()
        c.gpu.power.assert_not_called()
    def test_thermal_fault_is_refused_without_wait(self):
        from unittest.mock import patch
        from pearl_controller import GuardStop
        c=self.controller([self.reading(Hotspot=101)])
        with patch("pearl_controller.gpu_processes",return_value={}),patch("pearl_controller.time.sleep") as sleep:
            with self.assertRaisesRegex(GuardStop,"hotspot_temperature_guard"):c.idle_before_start()
        sleep.assert_not_called()
        c.gpu.power.assert_not_called()
if __name__=="__main__":unittest.main(verbosity=2)
