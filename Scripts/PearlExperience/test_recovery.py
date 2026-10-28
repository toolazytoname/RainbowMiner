"""Pure recovery policy checks; no sensors, power, miner or process calls."""
import unittest
from recover_session import power_action

class RecoveryTests(unittest.TestCase):
    def test_restores_only_the_known_mining_cap_after_exit(self):self.assertEqual(power_action(220,370,220),'restore-original')
    def test_existing_original_cap_needs_no_write(self):self.assertEqual(power_action(370,370,220),'already-restored')
    def test_external_cap_is_preserved(self):self.assertEqual(power_action(180,370,220),'preserve-external')
    def test_live_worker_prevents_power_restore(self):
        with self.assertRaisesRegex(RuntimeError,'has not exited'):power_action(220,370,220,worker_alive=True)
    def test_live_controller_prevents_power_restore(self):
        with self.assertRaisesRegex(RuntimeError,'has not exited'):power_action(220,370,220,controller_alive=True)
    def test_nonfinite_or_invalid_power_is_rejected(self):
        for bad in [float('nan'),float('inf'),0,-1,True,None]:
            for field in range(3):
                values=[220,370,220];values[field]=bad
                with self.subTest(value=bad,field=field),self.assertRaises(ValueError):power_action(*values)

if __name__=='__main__':unittest.main(verbosity=2)
