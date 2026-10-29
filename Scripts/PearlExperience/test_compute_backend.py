"""Host-only source-backend, fee policy, binary identity and telemetry checks."""
import hashlib,json,os,pathlib,tempfile,time,unittest
from compute_backend import select_compute_backend,read_source_stats,BackendStatsError

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
        self.exe=self.root/'soat-miner.exe';self.exe.write_bytes(b'host-only fixture, never executed')
        self.digest=hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.cfg={'backend':'soat','source_backend':{'executable':str(self.exe),'sha256':self.digest,'shape':'4096x65536','tile':'=ampere large s3 fold k64'},'wallet':'public-test','worker':'unit'}
        self.log=self.root/'miner.log'
    def tearDown(self):self.tmp.cleanup()
    def row(self,**changes):
        data={'algo':'pearl-pow','backend':'CUDA','unit':'T MAC/s','rate':51.23,'accepted':3,'rejected':0,'uptime_s':60,'timestamp_unix_ms':int(time.time()*1000)};data.update(changes);return data
    def write(self,row):self.log.write_text(json.dumps(row)+'\n',encoding='utf-8')
    def test_source_binary_identity_is_checked(self):
        b=select_compute_backend(self.cfg,self.root);b.verify_binary();self.exe.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash changed'):b.verify_binary()
    def test_source_uses_only_loopback_and_cuda_device_zero(self):
        b=select_compute_backend(self.cfg,self.root);args=b.command('stratum+tcp://127.0.0.1:23456',self.cfg)
        self.assertEqual(args[args.index('--device')+1],'0');self.assertEqual(args[args.index('--pool')+1],'127.0.0.1:23456')
        self.assertEqual(args[args.index('--wallet')+1],self.cfg['wallet']);self.assertEqual(b.rate_unit,'T MAC/s')
        for bad in ['stratum+tcp://foreign.example:23456','stratum+tcp://0.0.0.0:23456','stratum+tcp://user@127.0.0.1:23456','stratum+ssl://127.0.0.1:23456']:
            with self.subTest(url=bad),self.assertRaises(ValueError):b.command(bad,self.cfg)
    def test_only_validated_source_shape_and_tile_are_selected(self):
        for key,bad in [('shape','8192x65536'),('tile','=unvalidated'),('sha256','not-a-hash'),('executable','relative/soat-miner.exe')]:
            cfg=json.loads(json.dumps(self.cfg));cfg['source_backend'][key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):select_compute_backend(cfg,self.root)
    def test_confirmed_warpwide_tile_is_pinned_and_unconfirmed_early_tile_is_rejected(self):
        cfg=json.loads(json.dumps(self.cfg));cfg['source_backend']['tile']='=ampere warpwide large s3 fold k64'
        backend=select_compute_backend(cfg,self.root);backend.verify_binary()
        self.assertEqual(backend.environment()['SOAT_PEARL_TILE'],cfg['source_backend']['tile'])
        cfg['source_backend']['tile']='=ampere early large s3 fold k64'
        with self.assertRaises(ValueError):select_compute_backend(cfg,self.root)
    def test_source_environment_pins_and_disables_instrumentation(self):
        b=select_compute_backend(self.cfg,self.root);env=b.environment()
        self.assertEqual(env['SOAT_PEARL_SHAPE'],'4096x65536');self.assertEqual(env['SOAT_PEARL_TILE'],'=ampere large s3 fold k64');self.assertNotIn('SOAT_PEARL_PROFILE',env)
    def test_krig_relay_fee_cannot_be_silently_enabled(self):
        cfg={'exe_sha256':'0'*64}
        with self.assertRaisesRegex(ValueError,'3%'):select_compute_backend(cfg,self.root)
        cfg['allow_krig_relay_fee']=True;b=select_compute_backend(cfg,self.root);self.assertEqual(b.kind,'krig');self.assertEqual(b.rate_unit,'TH/s')
    def test_unknown_backend_never_falls_back(self):
        with self.assertRaisesRegex(ValueError,'no CPU fallback'):select_compute_backend({'backend':'cpu'},self.root)
    def test_source_values_keep_their_explicit_mac_units(self):
        self.write(self.row());s=read_source_stats(self.log)
        self.assertEqual(s['ReportedRate'],51.23);self.assertEqual(s['ReportedRateUnit'],'T MAC/s');self.assertNotIn('HashrateTHs',s);self.assertEqual(s['AcceptedShares'],3)
    def test_wrong_coin_backend_units_and_nonfinite_values_fail_closed(self):
        for change in [{'algo':'other'},{'backend':'CPU'},{'unit':'TH/s'},{'rate':float('nan')},{'rate':-1},{'accepted':True},{'rejected':1.5},{'uptime_s':-1}]:
            self.write(self.row(**change))
            with self.subTest(change=change),self.assertRaises(BackendStatsError):read_source_stats(self.log)
    def test_partial_latest_line_uses_last_complete_record(self):
        self.log.write_text('startup\n'+json.dumps(self.row())+'\n{"rate":',encoding='utf-8');self.assertEqual(read_source_stats(self.log)['AcceptedShares'],3)
    def test_stale_source_telemetry_ends_measurement(self):
        self.write(self.row());past=time.time()-60;os.utime(self.log,(past,past))
        with self.assertRaisesRegex(BackendStatsError,'stale'):read_source_stats(self.log)
    def test_missing_startup_stats_are_not_fabricated(self):
        self.assertIsNone(read_source_stats(self.log));self.log.write_text('starting\n');self.assertIsNone(read_source_stats(self.log))

    def test_warnings_cannot_refresh_expired_statistics(self):
        self.write(self.row(timestamp_unix_ms=int((time.time()-45)*1000)))
        with self.log.open('a') as stream:
            stream.write('{"event":"warn","msg":"waiting for a job"}\n')
        # The file is fresh; the only statistics record is not.
        self.assertLess(time.time()-self.log.stat().st_mtime,5)
        with self.assertRaisesRegex(BackendStatsError,'stale'):read_source_stats(self.log)
    def test_statistics_require_their_own_timestamp(self):
        row=self.row();row.pop('timestamp_unix_ms');self.write(row)
        with self.assertRaises(BackendStatsError):read_source_stats(self.log)
    def test_future_statistics_timestamp_is_rejected(self):
        self.write(self.row(timestamp_unix_ms=int((time.time()+60)*1000)))
        with self.assertRaisesRegex(BackendStatsError,'future'):read_source_stats(self.log)
    def test_zero_waiting_heartbeat_is_fresh_without_inventing_shares(self):
        self.write(self.row(rate=0,uptime_s=75));row=read_source_stats(self.log)
        self.assertEqual(row['ReportedRate'],0);self.assertEqual(row['AcceptedShares'],3)
        self.assertEqual(row['DeviceBackend'],'CUDA');self.assertGreater(row['BackendTimestampUnixMs'],0)
    def test_disappeared_records_do_not_reuse_the_previous_positive_rate(self):
        from types import SimpleNamespace
        from pearl_controller import Controller,GuardStop
        controller=Controller.__new__(Controller)
        controller.backend=SimpleNamespace(kind='soat');controller.backend_log=self.log
        controller.last_api={'ReportedRate':51.23}
        self.log.write_text('warning only\n')
        with self.assertRaisesRegex(GuardStop,'disappeared'):controller.api()

if __name__=='__main__':unittest.main(verbosity=2)
