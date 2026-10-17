import tempfile
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import automation
import auto_footage

class FakeVideos:
    def __init__(self, items): self.items = items
    def list(self, **kwargs): return self
    def execute(self): return {'items': self.items}
class FakeAPI:
    def __init__(self, items): self.items=items
    def videos(self): return FakeVideos(self.items)

class Downloads(unittest.TestCase):
    def test_topic_search_and_duplicate_exclusion(self):
        calls = []
        class Response:
            def __init__(self, items): self.items = items
            def execute(self): return {'items': self.items}
        class API:
            def search(self): return self
            def videos(self): return self
            def list(self, **kwargs):
                calls.append(kwargs)
                if kwargs['part'] == 'id,snippet':
                    return Response([{'id': {'videoId': 'new12345678'}}, {'id': {'videoId': 'old12345678'}}])
                return Response([{'id':'new12345678','status':{'license':'creativeCommon'},
                    'snippet':{'title':'GTA 5 police chase gameplay','channelTitle':'Creator'}}])
        with tempfile.TemporaryDirectory() as temp:
            config = {'sources':[{'video_id':'old12345678'}]}
            with patch('automation.youtube', return_value=API()):
                result = auto_footage.discover(Path(temp), config, 'GTA 5 police chase')
            self.assertEqual(result['video_id'], 'new12345678')
            self.assertIn('GTA 5 police chase', calls[0]['q'])
            self.assertEqual(calls[0]['videoLicense'], 'creativeCommon')
            self.assertNotIn('old12345678', calls[1]['id'])

    def test_non_cc_source_fails_closed_without_downloading(self):
        class Fake:
            def __init__(self, opts): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self,*args,**kwargs): raise AssertionError('Must check license first')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            config={'auto_discover':False,'sources':[{'video_id':'toQkKWEs2iE','enabled':True,'license':'creativeCommon','permission_statement':'Creative Commons','credit':'Creator','description':'GTA background','start_seconds':0,'end_seconds':120}]}
            automation.write(root/'footage-sources.json',config)
            with patch('automation.youtube',return_value=FakeAPI([{'id':'toQkKWEs2iE','status':{'license':'youtube'},'snippet':{'title':'GTA V gameplay'}}])), patch.dict(sys.modules,{'yt_dlp':types.SimpleNamespace(YoutubeDL=Fake)}):
                with self.assertRaisesRegex(ValueError,'no longer reports'):
                    auto_footage.sync(root)
            self.assertFalse((root/'media.json').exists())

    def test_cached_clips_are_reused_and_manual_entries_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source={'video_id':'toQkKWEs2iE','enabled':True,'license':'creativeCommon','permission_statement':'creativeCommon','credit':'Creator','description':'GTA background','start_seconds':0,'end_seconds':120}
            automation.write(root/'footage-sources.json',{'auto_discover':False,'sources':[source]})
            automation.write(root/'media.json',[{'file':'media/manual.mp4'}])
            folder=root/'media/auto/toQkKWEs2iE'; folder.mkdir(parents=True)
            for name in ['original.mp4','clip-0000.mp4','clip-0060.mp4']: (folder/name).touch()
            automation.write(folder/'permission.json',{'url':'https://www.youtube.com/watch?v=toQkKWEs2iE','license':'creativeCommon','checked':'YouTube Data API videos.list status.license'})
            with patch('automation.duration',return_value=720), patch.dict(sys.modules,{'yt_dlp':types.SimpleNamespace(YoutubeDL=None)}), patch('automation.youtube',return_value=FakeAPI([{'id':'toQkKWEs2iE','status':{'license':'creativeCommon'},'snippet':{'title':'GTA V gameplay'}}])):
                auto_footage.sync(root)
                auto_footage.sync(root)
            entries=automation.read(root/'media.json')
            self.assertEqual(len(entries),3)
            self.assertEqual(entries[0]['file'],'media/manual.mp4')

if __name__ == '__main__': unittest.main()
