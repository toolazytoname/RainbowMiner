import json,pathlib,tempfile,unittest
from unittest.mock import patch
import run_source_candidate_case as c
class CandidateManifestTests(unittest.TestCase):
    def fixture(self,folder):
        root=pathlib.Path(folder);build=root/"build/candidate";build.mkdir(parents=True);exe=build/"soat-miner.exe";exe.write_bytes(b"fixture, never executed");verifier=build/"test-pearl-mining-shape.exe";verifier.write_bytes(b"verifier fixture")
        proof=root/"correctness.json";proof.write_text(json.dumps({"phase":"passed","build":str(build),"cases":[{"name":f"{m}x{n}-fixture","binary_sha256":c.sha(verifier)} for m,n in [(256,768),(1024,1024),(4096,65536)]]}))
        result={"phase":"complete","plan":{"mode":"confirm","power_watts":220,"case_seconds":240,"executable":str(exe),"executable_sha256":c.sha(exe),"correctness_result":str(proof),"cases":[{"name":"A1","tile":"=ampere control"},{"name":"B","tile":"=ampere candidate","oracle_variant":"fixture"},{"name":"A2","tile":"=ampere control"}]},"review":{"comparison_valid":True,"candidate_confirmed_improvement":True},"cases":[{"name":n,"tile":"=ampere candidate" if n=="B" else "=ampere control","tail":{"tail_seconds":180,"steady":True}} for n in ["A1","B","A2"]]};path=root/"confirmation.json";path.write_text(json.dumps(result));return root,exe,path,result
    def test_validated_candidate_is_constructed_without_gpu_or_config_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root,exe,path,result=self.fixture(folder)
            with patch.object(c,"SOURCE_PROJECT",root):backend=c.candidate_from_confirmation(path)
            self.assertEqual(backend.executable,exe.resolve());self.assertEqual(backend.tile,"=ampere candidate");self.assertEqual(backend.rate_unit,"T MAC/s")
    def test_failed_quality_or_missing_material_gain_is_rejected(self):
        for key in ["comparison_valid","candidate_confirmed_improvement"]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as folder:
                root,exe,path,result=self.fixture(folder);result["review"][key]=False;path.write_text(json.dumps(result))
                with patch.object(c,"SOURCE_PROJECT",root),self.assertRaises(ValueError):c.candidate_from_confirmation(path)
    def test_changed_binary_and_missing_full_buffer_proof_are_rejected(self):
        for mode in ["binary","proof"]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                root,exe,path,result=self.fixture(folder)
                if mode=="binary":exe.write_bytes(b"changed")
                else:
                    proof=pathlib.Path(result["plan"]["correctness_result"]);d=json.loads(proof.read_text());d["cases"].pop();proof.write_text(json.dumps(d))
                with patch.object(c,"SOURCE_PROJECT",root),self.assertRaises(ValueError):c.candidate_from_confirmation(path)
    def test_invalid_confirmation_never_constructs_gpu_management(self):
        with tempfile.TemporaryDirectory() as folder:
            root,exe,path,result=self.fixture(folder);result["phase"]="stopped";path.write_text(json.dumps(result))
            with patch.object(c,"SOURCE_PROJECT",root),patch.object(c,"CandidateExperience") as constructor,self.assertRaises(ValueError):c.run_case(path,5,root/"receipt.json")
            constructor.assert_not_called()
    def test_mismatched_tile_or_outside_project_is_rejected(self):
        for mode in ["tile","path"]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                root,exe,path,result=self.fixture(folder)
                if mode=="tile":result["cases"][1]["tile"]="=ampere other";path.write_text(json.dumps(result))
                with patch.object(c,"SOURCE_PROJECT",root if mode=="tile" else root/"other"),self.assertRaises(ValueError):c.candidate_from_confirmation(path)
    def test_first_share_stop_preserves_original_stop_precedence(self):
        obj=object.__new__(c.CandidateExperience);obj.s={"AcceptedShares":1}
        with patch.object(c.Experience,"check_stop",return_value=None),self.assertRaisesRegex(c.EndSession,"candidate_first_accepted_share"):obj.check_stop()
        with patch.object(c.Experience,"check_stop",side_effect=c.EndSession("user_stop")),self.assertRaisesRegex(c.EndSession,"user_stop"):obj.check_stop()
if __name__=="__main__":unittest.main(verbosity=2)
