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
