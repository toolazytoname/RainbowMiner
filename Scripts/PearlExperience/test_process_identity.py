"""Windows handle tests against bounded owned CPU children; no GPU work."""
import os,subprocess,time,unittest
from process_identity import capture_owned_child,capture_controller,ProcessHandle,identity_matches,file_hash

@unittest.skipUnless(os.name=='nt','Windows process handles')
class IdentityTests(unittest.TestCase):
    def test_wrong_creation_time_cannot_terminate_target_or_outside_child(self):
        base=capture_controller()['Executable']
        children=[subprocess.Popen([base,'-c','import time;time.sleep(30)'],creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS) for _ in range(2)]
        target,outside=children
        try:
            record=capture_owned_child(target);digest=file_hash(record['Executable']);wrong=dict(record,CreationFileTime=record['CreationFileTime']+1)
            with ProcessHandle(target.pid) as handle:
                with self.assertRaisesRegex(RuntimeError,'identity mismatch'):handle.terminate_owned(wrong,record['Executable'],digest)
                self.assertTrue(handle.running());self.assertIsNone(outside.poll())
                self.assertTrue(handle.terminate_owned(record,record['Executable'],digest));self.assertFalse(handle.running())
            target.wait(timeout=5);self.assertIsNone(outside.poll())
        finally:
            for child in children:
                if child.poll() is None:child.terminate()
                child.wait(timeout=5)
    def test_wrong_image_or_hash_fails_without_process_mutation(self):
        record=capture_controller();actual={k:record[k] for k in ['Pid','Executable','CreationFileTime']}
        self.assertTrue(identity_matches(record,actual,record['Executable'],record['Sha256']))
        self.assertFalse(identity_matches(record,actual,record['Executable']+'.foreign',record['Sha256']))
        self.assertFalse(identity_matches(record,actual,record['Executable'],'0'*64))
        self.assertFalse(identity_matches(dict(record,Pid=record['Pid']+1),actual,record['Executable'],record['Sha256']))
    def test_system_pid_is_never_opened_for_termination(self):
        for pid in [0,1,4,True,None]:
            with self.subTest(pid=pid),self.assertRaises(ValueError):ProcessHandle(pid)

if __name__=='__main__':unittest.main(verbosity=2)
