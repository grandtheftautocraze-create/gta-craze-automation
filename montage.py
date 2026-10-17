"""Build varied, motion-checked montages from the approved local catalog."""
import subprocess


def motion_score(path, offset, seconds):
    raw = subprocess.check_output([
        'ffmpeg', '-nostdin', '-v', 'error', '-ss', str(offset), '-i', str(path),
        '-t', str(seconds), '-vf', 'fps=3,scale=64:64,format=gray',
        '-an', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], timeout=60)
    frames = [raw[i:i+4096] for i in range(0, len(raw)-4095, 4096)]
    changes = [sum(abs(a-b) for a,b in zip(x,y))/4096 for x,y in zip(frames,frames[1:])]
    return sorted(changes)[len(changes)//2] if changes else 0


def build(root, jobdir, clips, seconds):
    from automation import read, write, duration
    history_path = root / 'data' / 'shot-usage.json'
    history = read(history_path) if history_path.exists() else {}
    candidates = []
    for clip in clips:
        length = duration(root / clip['file'])
        # Disjoint windows spread throughout each cached excerpt, avoiding intros.
        for offset in range(2, max(2, int(length)-4), 5):
            candidates.append(dict(clip=clip, offset=offset,
                key=clip['file'] + '@' + str(offset),
                source=clip.get('auto_source', clip['permission_reference'])))
    if len({c['source'] for c in candidates}) < 2:
        raise ValueError('Montage requires at least two approved footage sources.')
    chosen, used, source_counts = [], set(), {}
    elapsed = 0.0
    while elapsed < seconds - 0.01:
        length = min([2.4, 3.2, 2.8, 3.6][len(chosen) % 4], seconds-elapsed)
        last = chosen[-1]['source'] if chosen else None
        ranked = sorted((c for c in candidates if c['key'] not in used and c['source'] != last),
            key=lambda c:(source_counts.get(c['source'],0), history.get(c['key'],0), -next(i for i, clip in enumerate(clips) if clip['file'] == c['clip']['file']), c['key']))
        accepted = None
        for candidate in ranked[:40]:
            used.add(candidate['key'])
            score = motion_score(root / candidate['clip']['file'], candidate['offset'], max(length, 1))
            if score < 1.2:
                continue
            accepted = dict(candidate, seconds=length, motion_score=round(score,2))
            break
        if accepted is None:
            raise ValueError('Not enough varied moving footage; holding video instead of repeating still shots.')
        chosen.append(accepted)
        source_counts[accepted['source']] = source_counts.get(accepted['source'],0)+1
        elapsed += length
    write(jobdir / 'shot-plan.json', chosen)
    for index, shot in enumerate(chosen):
        subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-ss',str(shot['offset']),
            '-i',str((root / shot['clip']['file']).resolve()),'-t',str(shot['seconds']),
            '-vf','fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1',
            '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
            str(jobdir / f'shot-{index:03d}.mp4')],check=True,timeout=180)
    (jobdir / 'shots.txt').write_text(''.join(f"file 'shot-{i:03d}.mp4'\n" for i in range(len(chosen))),encoding='utf-8')
    subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','1',
        '-i','shots.txt','-c','copy','montage.mp4'],cwd=jobdir,check=True,timeout=180)
    if abs(duration(jobdir / 'montage.mp4') - seconds) > 0.5:
        raise ValueError('Montage duration mismatch')
    usage_path = root / 'data' / 'clip-usage.json'
    usage = read(usage_path) if usage_path.exists() else {}
    for shot in chosen:
        history[shot['key']] = history.get(shot['key'],0)+1
        name = shot['clip']['file']
        usage[name] = usage.get(name,0)+1
    write(history_path,history)
    write(usage_path,usage)
    print(f'Montage: {len(chosen)} moving shots from {len(source_counts)} sources',flush=True)
    return chosen
