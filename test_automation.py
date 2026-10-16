import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import automation as a

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
        script = dict(title='Example', narration='word ' * 70, ready=True)
        with self.assertRaises(ValueError): a.validate_script(script, 'story')
        script['narration'] = 'Fictional story. ' + script['narration']
        a.validate_script(script, 'story')
        script['ready'] = False
        with self.assertRaises(ValueError): a.validate_script(script, 'news')

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
