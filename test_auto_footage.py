import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import automation
import auto_footage

class Downloads(unittest.TestCase):
    def test_missing_live_permission_prevents_download_and_catalog(self):
        class Fake:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, *args, **kwargs):
                return {'id':'toQkKWEs2iE', 'description':'No permission here', 'duration':720}
            def download(self, urls):
                raise AssertionError('Must not download')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            automation.write(root/'footage-sources.json', [{'video_id':'toQkKWEs2iE',
                'enabled':True,'permission_confirmed':True,'permission_statement':'Free to use my videos in your clips'}])
            with patch.dict(sys.modules, {'yt_dlp':types.SimpleNamespace(YoutubeDL=Fake)}), patch('shutil.which', return_value='/bin/ffmpeg'):
                with self.assertRaisesRegex(ValueError, 'Reuse statement'):
                    auto_footage.sync(root)
            self.assertFalse((root/'media.json').exists())

    def test_cache_reuse_preserves_manual_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = {'video_id':'toQkKWEs2iE','enabled':True,'permission_confirmed':True,
                'permission_statement':'Free to use my videos in your clips',
                'start_seconds':35,'end_seconds':155,'description':'Background', 'credit':'Creator'}
            automation.write(root/'footage-sources.json', [source])
            automation.write(root/'media.json', [{'file':'media/manual.mp4'}])
            folder = root/'media/auto/toQkKWEs2iE'; folder.mkdir(parents=True)
            for name in ['original.mp4','clip-0035.mp4','clip-0095.mp4']:
                (folder/name).touch()
            automation.write(folder/'permission.json', {'url':'https://www.youtube.com/watch?v=toQkKWEs2iE',
                'statement':source['permission_statement'],
                'basis':'Description supplied by user; checked against live description on download.'})
            with patch.dict(sys.modules, {'yt_dlp':types.SimpleNamespace(YoutubeDL=None)}), patch('automation.duration',return_value=720):
                auto_footage.sync(root)
                auto_footage.sync(root)
            entries = automation.read(root/'media.json')
            self.assertEqual(len(entries),3)
            self.assertEqual(entries[0]['file'],'media/manual.mp4')

if __name__ == '__main__': unittest.main()
