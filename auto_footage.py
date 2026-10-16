"""Discover CC BY GTA footage through YouTube API, download, and cache silent excerpts."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def read_sources(path):
    if not path.exists():
        return {'auto_discover': True, 'queries': ['GTA 5 gameplay no commentary'], 'sources': []}
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    # Migrate the earlier single-source list format.
    if isinstance(value, list):
        return {'auto_discover': False, 'queries': ['GTA 5 gameplay no commentary'], 'sources': value}
    return value


def add_deno_to_path():
    if os.name != 'nt' or shutil.which('deno'):
        return
    local = Path(os.environ.get('LOCALAPPDATA', ''))
    roots = [local / 'Microsoft' / 'WinGet' / 'Packages', Path(os.environ.get('USERPROFILE', '')) / '.deno' / 'bin']
    for root in roots:
        if not root.exists():
            continue
        matches = list(root.glob('DenoLand.Deno*/deno.exe')) if 'WinGet' in str(root) else list(root.glob('deno.exe'))
        if matches:
            os.environ['PATH'] = str(matches[0].parent) + os.pathsep + os.environ.get('PATH', '')
            return


def discover(root, config):
    from automation import youtube, write
    api = youtube()
    sources = config.setdefault('sources', [])
    known = {s.get('video_id') for s in sources}
    query = (config.get('queries') or ['GTA 5 gameplay no commentary'])[0]
    results = api.search().list(part='id,snippet', q=query, type='video', videoLicense='creativeCommon',
                                videoDuration='medium', order='relevance', maxResults=50).execute().get('items', [])
    ids = [item.get('id', {}).get('videoId') for item in results]
    ids = [i for i in ids if i and i not in known]
    for offset in range(0, len(ids), 50):
        response = api.videos().list(part='snippet,status,contentDetails', id=','.join(ids[offset:offset+50])).execute()
        for video in response.get('items', []):
            title = video.get('snippet', {}).get('title', '')
            if video.get('status', {}).get('license') != 'creativeCommon':
                continue
            if not re.search(r'\b(gta|grand theft auto)\b', title, re.I):
                continue
            vid = video['id']
            item = {'video_id': vid, 'enabled': True, 'permission_confirmed': True,
                    'permission_statement': 'YouTube Data API status.license=creativeCommon',
                    'credit': f"{video['snippet'].get('channelTitle','Creator')}, ‘{title}’ — Creative Commons Attribution (CC BY)",
                    'description': f"GTA gameplay footage from {title}; silent illustrative background, not GTA 6 footage.",
                    'start_seconds': 0, 'end_seconds': 360, 'license': 'creativeCommon'}
            sources.append(item)
            write(root / 'footage-sources.json', config)
            print('Auto-selected Creative Commons source:', item['credit'], flush=True)
            return item
    raise ValueError('No new GTA Creative Commons videos found. No paid generation or upload was attempted.')


def sync(root):
    from yt_dlp import YoutubeDL
    from automation import read, write, duration
    add_deno_to_path()
    sources_path = root / 'footage-sources.json'
    config = read_sources(sources_path)
    catalog_path = root / 'media.json'
    catalog = read(catalog_path) if catalog_path.exists() else []
    usage_path = root / 'data' / 'clip-usage.json'
    usage = read(usage_path) if usage_path.exists() else {}
    if config.get('auto_discover'):
        known_catalog = [entry for entry in catalog if entry.get('auto_source')]
        if not known_catalog or all(usage.get(entry['file'], 0) > 0 for entry in known_catalog):
            discover(root, config)
    for source in config.get('sources', []):
        if source.get('enabled') is not True:
            continue
        video_id = source['video_id']
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise ValueError('Invalid footage video ID')
        url = 'https://www.youtube.com/watch?v=' + video_id
        folder = root / 'media' / 'auto' / video_id
        folder.mkdir(parents=True, exist_ok=True)
        original = folder / 'original.mp4'
        receipt = folder / 'permission.json'
        expected = {'url': url, 'license': 'creativeCommon', 'checked': 'YouTube Data API videos.list status.license'}
        from automation import youtube
        videos = youtube().videos().list(part='snippet,status', id=video_id).execute().get('items', [])
        if not videos or videos[0].get('status', {}).get('license') != 'creativeCommon':
            raise ValueError('YouTube no longer reports this source as Creative Commons; source held.')
        snippet = videos[0].get('snippet', {})
        if not re.search(r'\b(gta|grand theft auto)\b', snippet.get('title', ''), re.I):
            raise ValueError('Source title is not clearly GTA gameplay; source held.')
        if source.get('license') != 'creativeCommon' and 'creativeCommon' not in source.get('permission_statement', ''):
            raise ValueError('Source has no verified Creative Commons declaration.')
        if not original.exists() or not receipt.exists() or read(receipt) != expected:
            print('Verified Creative Commons license; fetching:', url, flush=True)
            opts = {'noplaylist': True, 'quiet': True, 'socket_timeout': 30, 'retries': 2,
                    'fragment_retries': 2, 'format': 'bestvideo[ext=mp4][height<=1080]/best[ext=mp4][height<=1080]',
                    'outtmpl': str(folder / 'original.%(ext)s'),
                    'ffmpeg_location': str(Path(shutil.which('ffmpeg')).parent),
                    'max_filesize': 1500 * 1024 * 1024}
            with YoutubeDL(opts) as downloader:
                info = downloader.extract_info(url, download=False)
                if info.get('id') != video_id or info.get('is_live') or not 60 <= (info.get('duration') or 0) <= 3600:
                    raise ValueError('Source must be a finished GTA video between 1 and 60 minutes.')
                write(folder / 'source-details.json', {'title': snippet.get('title'), 'uploader': snippet.get('channelTitle'),
                    'url': url, 'license': 'Creative Commons Attribution (CC BY)'})
                downloader.download([url])
            if not original.is_file():
                raise ValueError('Source download did not produce an MP4; check downloader output.')
            duration(original)
            write(receipt, expected)
        end = min(float(source.get('end_seconds', 360)), duration(original))
        start = float(source.get('start_seconds', 0))
        if start < 0 or end - start < 60:
            raise ValueError('Source requires at least 60 usable seconds')
        entries = []
        credit = source['credit']
        for position in range(int(start), int(end) - 59, 60):
            target = folder / f'clip-{position:04d}.mp4'
            if not target.exists():
                pending = folder / f'clip-{position:04d}.pending.mp4'
                subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-ss', str(position), '-i', str(original), '-t', '60',
                    '-map', '0:v:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', str(pending)], stdin=subprocess.DEVNULL, check=True, timeout=600)
                if duration(pending) < 59:
                    raise ValueError('Downloaded excerpt is incomplete')
                pending.replace(target)
            entries.append({'file': target.relative_to(root).as_posix(),
                'description': source['description'] + f' Excerpt begins at {position}s; visuals not independently inspected.',
                'credit': credit, 'permission_reference': url + ' — Creative Commons Attribution (CC BY)',
                'permission_confirmed': True, 'auto_source': video_id})
        catalog = [e for e in catalog if e.get('auto_source') != video_id] + entries
        write(catalog_path, catalog)
        print(f'Ready: {len(entries)} cached silent excerpts from {video_id}', flush=True)
    return catalog
