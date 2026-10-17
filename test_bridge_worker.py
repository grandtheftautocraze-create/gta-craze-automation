import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import bridge_worker as b

class FakeAPI:
    def __init__(self, jobs):
        self.jobs, self.reports = jobs, []
    def get(self, path):
        return {'version': 1, 'jobs': self.jobs}, 'sha'
    def publish(self, state):
        self.reports.append(copy.deepcopy(state))

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.clock = datetime(2026, 10, 17, 10, tzinfo=timezone.utc)
        self.activated = self.clock - timedelta(minutes=10)
        self.job = {'id': 'request-1', 'action': 'generate_upload', 'format': 'community',
                    'created_at': (self.clock - timedelta(minutes=1)).isoformat(),
                    'expires_at': (self.clock + timedelta(hours=1)).isoformat()}
    def test_queue_cannot_supply_commands_or_paths(self):
        for field, value in [('command', 'calc.exe'), ('format', 'community & calc.exe'), ('id', '../escape')]:
            job = dict(self.job, **{field: value})
            self.assertFalse(b.valid_job(job, self.activated, self.clock))
    def test_expired_preinstallation_and_long_lived_requests_rejected(self):
        for edits in [dict(expires_at=self.clock.isoformat()),
                      dict(created_at=(self.activated - timedelta(seconds=1)).isoformat()),
                      dict(expires_at=(self.clock + timedelta(days=2)).isoformat())]:
            self.assertFalse(b.valid_job(dict(self.job, **edits), self.activated, self.clock))
    def test_request_executes_once_across_repeated_polls(self):
        with TemporaryDirectory() as td, patch.object(b, 'DATA', Path(td)):
            calls = []
            api = FakeAPI([self.job])
            path = Path(td) / 'state.json'
            def run(job):
                self.assertEqual(b.read(path)['jobs'][job['id']]['state'], 'started')
                calls.append(job['id'])
                return {'state': 'uploaded', 'video_url': 'https://www.youtube.com/watch?v=abcdefghijk'}
            b.process(api, self.activated, path, self.clock, run)
            b.process(api, self.activated, path, self.clock, run)
            self.assertEqual(calls, ['request-1'])
    def test_crash_claim_requires_review_and_never_repeats(self):
        with TemporaryDirectory() as td, patch.object(b, 'DATA', Path(td)):
            path = Path(td) / 'state.json'
            b.write(path, {'jobs': {'request-1': {'state': 'started', 'action': 'generate_upload',
                     'started_at': self.clock.isoformat()}}, 'dirty': True})
            calls = []
            b.process(FakeAPI([self.job]), self.activated, path, self.clock, lambda j: calls.append(j))
            self.assertFalse(calls)
            self.assertEqual(b.read(path)['jobs']['request-1']['state'], 'needs_review')
    def test_six_remote_generations_per_rolling_day(self):
        with TemporaryDirectory() as td, patch.object(b, 'DATA', Path(td)):
            path = Path(td) / 'state.json'
            records = {str(i): {'state': 'uploaded', 'action': 'generate_upload',
                       'started_at': self.clock.isoformat()} for i in range(6)}
            b.write(path, {'jobs': records, 'dirty': False})
            calls = []
            b.process(FakeAPI([self.job]), self.activated, path, self.clock, lambda j: calls.append(j))
            self.assertFalse(calls)
    def test_failed_start_report_never_runs_paid_generation(self):
        with TemporaryDirectory() as td, patch.object(b, 'DATA', Path(td)):
            path = Path(td) / 'state.json'
            b.write(path, {'jobs': {}, 'dirty': False})
            api = FakeAPI([self.job])
            calls = []
            with patch.object(api, 'publish', side_effect=OSError('offline')):
                with self.assertRaises(OSError):
                    b.process(api, self.activated, path, self.clock, lambda j: calls.append(j))
            self.assertFalse(calls)
            self.assertEqual(b.read(path)['jobs']['request-1']['state'], 'held')

if __name__ == '__main__':
    unittest.main()
