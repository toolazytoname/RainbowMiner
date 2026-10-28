"""CPU checks for explicit, non-persistent backend and fee selection."""
import json,pathlib,tempfile,unittest
from unittest.mock import Mock,patch
import run_backend_comparison_case as bc
BASE={"backend":"soat","allow_krig_relay_fee":False,"default_minutes":15,"wallet":"public-fixture","worker":"fixture","pool":"stratum+ssl://prl-hk.kryptex.network:8048","power_watts":220}
class OneCasePolicy(unittest.TestCase):
    def test_fee_choice_does_not_mutate_default_config(self):
        result=bc.case_config(BASE,"krig",15,3)
        self.assertEqual(BASE["backend"],"soat");self.assertFalse(BASE["allow_krig_relay_fee"])
        self.assertTrue(result["allow_krig_relay_fee"]);self.assertEqual(result["backend"],"krig")
        for key in ("wallet","worker","pool","power_watts"):self.assertEqual(result[key],BASE[key])
    def test_fee_ack_required_before_controller_construction(self):
        with patch.object(bc,"Experience") as ctor:
            with self.assertRaises(ValueError):bc.run_case("krig",15,pathlib.Path("unused.json"))
            ctor.assert_not_called()
    def test_source_rejects_fee_flag(self):
        with self.assertRaises(ValueError):bc.case_config(BASE,"soat",15,3)
    def test_duration_is_bounded(self):
        for minutes in (0,16):
            with self.subTest(minutes=minutes),self.assertRaises(ValueError):bc.case_config(BASE,"krig",minutes,3)
    def test_failure_does_not_persist_fee_or_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);config=root/"mining-config.json";raw=json.dumps(BASE);config.write_text(raw)
            experience=Mock();experience.cfg=dict(BASE);experience.execute.side_effect=RuntimeError("synthetic guard")
            receipt=root/"case/entry.json"
            with patch.object(bc,"ROOT",root),patch.object(bc,"Experience",return_value=experience),patch.object(bc,"select_compute_backend",return_value="pinned-krig"):
                with self.assertRaises(RuntimeError):bc.run_case("krig",15,receipt,3)
            self.assertEqual(config.read_text(),raw);self.assertEqual(experience.execute.call_count,1)
            state=json.loads(receipt.read_text());self.assertTrue(state["production_config_unchanged"]);self.assertEqual(state["status"],"failed")
if __name__=="__main__":unittest.main()
