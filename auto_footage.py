"""Download explicitly approved sources; cache originals and rotate silent excerpts."""
import json
from pathlib import Path
import shutil
import subprocess


def sync(root):
    from yt_dlp import YoutubeDL
    from automation import read, write, duration
    sources_path = root / 'footage-sources.json'
    if not sources_path.exists():
        return
    catalog_path = root / 'media.json'
    catalog = read(catalog_path) if catalog_path.exists() else []
    for source in read(sources_path):
        if source.get('enabled') is not True or source.get('permission_confirmed') is not True:
            continue
        video_id = source['video_id']
        import re
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise ValueError('Invalid approved YouTube video ID')
        url = 'https://www.youtube.com/watch?v=' + video_id
        folder = root / 'media' / 'auto' / video_id
        folder.mkdir(parents=True, exist_ok=True)
        original = folder / 'original.mp4'
        receipt = folder / 'permission.json'
        expected = {'url': url, 'statement': source['permission_statement'],
                    'basis': 'Description supplied by user; checked against live description on download.'}
        if not original.exists() or not receipt.exists() or read(receipt) != expected:
            print('Checking approved source:', url, flush=True)
            opts = {'noplaylist': True, 'quiet': True, 'socket_timeout': 30,
                    'retries': 2, 'fragment_retries': 2,
                    'format': 'bestvideo[ext=mp4][height<=1080]/best[ext=mp4][height<=1080]',
                    'outtmpl': str(folder / 'original.%(ext)s'),
                    'ffmpeg_location': str(Path(shutil.which('ffmpeg')).parent),
                    'max_filesize': 1500 * 1024 * 1024}
            with YoutubeDL(opts) as downloader:
                info = downloader.extract_info(url, download=False)
                if info.get('id') != video_id or info.get('is_live'):
                    raise ValueError('Expected a single finished video')
                description = info.get('description') or ''
                normalize = lambda s: ' '.join(s.casefold().split())
                if normalize(source['permission_statement']) not in normalize(description):
                    raise ValueError('Reuse statement was not found in the live description. Source held; no download.')
                if not 60 <= (info.get('duration') or 0) <= 3600:
                    raise ValueError('Source duration must be 1-60 minutes')
                write(folder / 'source-details.json', {'title': info.get('title'),
                      'uploader': info.get('uploader'), 'description': description, 'url': url})
                downloader.download([url])
            if not original.is_file():
                raise ValueError('Source download did not produce an MP4; check downloader output.')
            duration(original)
            write(receipt, expected)
        end = min(float(source['end_seconds']), duration(original))
        start = float(source['start_seconds'])
        if start < 0 or end - start < 60:
            raise ValueError('Source requires at least 60 usable seconds')
        entries = []
        for position in range(int(start), int(end) - 59, 60):
            target = folder / f'clip-{position:04d}.mp4'
            if not target.exists():
                pending = folder / f'clip-{position:04d}.pending.mp4'
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(position),
                    '-i', str(original), '-t', '60', '-map', '0:v:0', '-an',
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(pending)],
                    check=True, timeout=600)
                if duration(pending) < 59:
                    raise ValueError('Downloaded excerpt is incomplete')
                pending.replace(target)
            entries.append({'file': target.relative_to(root).as_posix(),
                'description': source['description'] + f' Excerpt beginning at {position}s; visuals not independently inspected.',
                'credit': source['credit'] + ' — ' + url,
                'permission_reference': url + ' — ' + source['permission_statement'],
                'permission_confirmed': True, 'auto_source': video_id})
        catalog = [e for e in catalog if e.get('auto_source') != video_id] + entries
        write(catalog_path, catalog)
        print(f'Ready: {len(entries)} cached silent excerpts from {video_id}', flush=True)
