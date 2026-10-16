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

    def test_caption_escape_and_endpoint(self):
        result = a.captions('Hello {override} \\N world today', 25)
        self.assertNotIn('{override}', result)
        self.assertIn('0:00:25.00', result)

    def test_community_caption_style_is_distinct(self):
        explainer = a.captions('One two three four five six', 20)
        community = a.captions('One two three four five six', 20, 'community')
        self.assertIn('GTA CRAZE  /  QUICK BREAKDOWN', explainer)
        self.assertIn('GTA COMMUNITY', community)
        self.assertNotEqual(explainer, community)

if __name__ == '__main__': unittest.main()
