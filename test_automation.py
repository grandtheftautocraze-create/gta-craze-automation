import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import automation as a

def script_payload():
    return dict(
        title='GTA 5 police chases have a hidden detail',
        narration='A useful fact about GTA gameplay. ' * 13,
        primary_keyword='GTA 5 police chases',
        description=('GTA 5 police chases change as your wanted level rises. This Short explains the detail and why it matters. What would you try?'),
        tags=['GTA 5 police chases', 'Grand Theft Auto V', 'GTA 5 wanted level', 'GTA gameplay'],
        hashtags=['#GTA5', '#GTAShorts', '#Shorts'],
        ready=True,
    )

class Tests(unittest.TestCase):
    def test_budget_counts_failed_attempts(self):
        with TemporaryDirectory() as t, patch.object(a, 'DATA', Path(t)):
            db = a.database()
            a.reserve(db, 'one', 1)
            db.execute("UPDATE jobs SET status='failed'")
            db.commit()
            with self.assertRaises(ValueError):
                a.reserve(db, 'two', 1)
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
            db.close()

    def test_permission_gate(self):
        with TemporaryDirectory() as t, patch.object(a, 'ROOT', Path(t)):
            media = Path(t) / 'media'
            media.mkdir()
            (media / 'clip.mp4').touch()
            entry = dict(file='media/clip.mp4', description='Driving', credit='Creator', permission_reference='agreement', permission_confirmed=False)
            a.write(Path(t) / 'media.json', [entry])
            with self.assertRaises(ValueError): a.media_entries()
            entry['permission_confirmed'] = True
            a.write(Path(t) / 'media.json', [entry])
            self.assertEqual(len(a.media_entries()), 1)
            entry['file'] = '../outside.mp4'
            a.write(Path(t) / 'media.json', [entry])
            with self.assertRaises(ValueError): a.media_entries()

    def test_fiction_and_insufficient_research(self):
        script = script_payload()
        with self.assertRaises(ValueError): a.validate_script(script, 'story')
        script['narration'] = 'Fictional story. ' + script['narration']
        a.validate_script(script, 'story')
        script['ready'] = False
        with self.assertRaises(ValueError): a.validate_script(script, 'news')

    def test_seo_metadata_reconciles_keyword_and_bounds_tags(self):
        script = script_payload()
        self.assertEqual(a.validate_script(script, 'details')['primary_keyword'], 'GTA 5 police chases')
        script['title'] = 'A hidden detail in this game'
        repaired = a.validate_script(script, 'details')
        self.assertEqual(repaired['primary_keyword'], 'hidden detail game')
        self.assertIn(repaired['primary_keyword'], repaired['description'][:220])
        script = script_payload()
        script['hashtags'].append('#Gaming')
        with self.assertRaisesRegex(ValueError, '2-3 relevant hashtags'):
            a.validate_script(script, 'details')

    def test_caption_measured_timing_and_position(self):
        words = [{'word': 'Hello', 'start': 0.4, 'end': 0.8},
                 {'word': '{world}', 'start': 1.7, 'end': 2.1}]
        result = a.captions(words, 3)
        self.assertIn('0:00:00.40,0:00:00.80', result)
        self.assertIn('0:00:01.70,0:00:02.10', result)
        self.assertIn(r'\pos(510,1210)', result)
        self.assertNotIn('{world}', result)

    def test_caption_handles_zero_duration_and_small_overlap(self):
        result = a.captions([
            {'word':'GTA','start':0.2,'end':0.2},
            {'word':'five','start':0.2,'end':0.6},
            {'word':'chaos','start':0.55,'end':1.0}], 2)
        self.assertIn('GTA five', result)
        self.assertIn('0:00:00.60,0:00:01.00', result)
        with self.assertRaises(ValueError):
            a.captions([{'word':'one','start':0,'end':1},
                        {'word':'two','start':0.2,'end':1.5}], 2)

    def test_caption_rejects_missing_and_bad_timings(self):
        for words in [[], 'text', [{'word':'x', 'start':2, 'end':1}]]:
            with self.assertRaises(ValueError):
                a.captions(words, 3)

if __name__ == '__main__': unittest.main()
