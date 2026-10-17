"""Fixed-action GitHub queue worker. Secrets and production logs stay on this PC."""
import argparse
import base64
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from filelock import FileLock, Timeout

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
REPO = 'grandtheftautocraze-create/gta-craze-automation'
QUEUE = 'bridge/queue.json'
STATUS = 'bridge/status.json'


def now():
    return datetime.now(timezone.utc)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    tmp.replace(path)


def stamp(value):
    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Timezone required')
    return value


def valid_job(job, activated, clock):
    if not isinstance(job, dict) or set(job) - {'id', 'action', 'format', 'created_at', 'expires_at'}:
        return False
    if not isinstance(job.get('id'), str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', job['id']):
        return False
    if job.get('action') not in ('ping', 'generate_upload'):
        return False
    if job['action'] == 'generate_upload' and job.get('format') not in ('community', 'explainer'):
        return False
    try:
        created, expires = stamp(job['created_at']), stamp(job['expires_at'])
        return activated <= created <= clock < expires <= created + timedelta(hours=24)
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def token():
    # Export-Clixml SecureString can only be decrypted by the Windows user who saved it.
    command = "$s=Import-Clixml -LiteralPath 'data/bridge-token.xml'; [System.Net.NetworkCredential]::new('', $s).Password"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError('Could not unlock GitHub credential; rerun installer under the same Windows account')
    return result.stdout.strip()


class GitHub:
    def __init__(self, credential):
        self.credential = credential

    def request(self, path, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request('https://api.github.com/repos/' + REPO + '/contents/' + path,
            data=payload, method='PUT' if payload is not None else 'GET', headers={
                'Authorization': 'Bearer ' + self.credential,
                'Accept': 'application/vnd.github+json', 'User-Agent': 'GTA-Craze-Local-Bridge',
                'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def get(self, path):
        obj = self.request(path)
        if obj.get('encoding') != 'base64' or obj.get('size', 0) > 200000:
            raise ValueError('Invalid bridge document')
        return json.loads(base64.b64decode(obj['content'])), obj['sha']

    def publish(self, state):
        _, sha = self.get(STATUS)
        # Only these fields leave the computer; never send logs, tokens or local paths.
        recent = list(state['jobs'].items())[-20:]
        body = {'version': 1, 'checked_at': now().isoformat(), 'connection': 'verified',
                'jobs': [{'id': key, **value} for key, value in recent]}
        self.request(STATUS, {'message': 'Report local bridge status', 'sha': sha,
            'content': base64.b64encode(json.dumps(body, indent=2).encode()).decode()})


def execute(job):
    if job['action'] == 'ping':
        return {'state': 'pong'}
    # This bridge only invokes the installed program with two fixed format choices.
    # It never executes shell commands, paths, URLs or code supplied by the queue.
    from automation import config
    cfg = config()
    if cfg.get('mode') != 'publish' or cfg.get('privacy') != 'public':
        return {'state': 'held', 'reason': 'Local configuration is not publish/public'}
    log = DATA / ('bridge-' + job['id'] + '.log')
    with log.open('w', encoding='utf-8') as output:
        result = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), str(ROOT / 'automation.py'),
                                 'run', '--format', job['format']], cwd=ROOT,
                                stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                timeout=5400, shell=False)
    contents = log.read_text(encoding='utf-8', errors='replace')
    found = re.search(r'Uploaded: https://www.youtube.com/watch\?v=([A-Za-z0-9_-]{11})', contents)
    if found:
        return {'state': 'uploaded', 'video_url': 'https://www.youtube.com/watch?v=' + found.group(1)}
    return {'state': 'needs_review', 'reason': 'No confirmed upload; inspect local log and YouTube Studio',
            'exit_code': result.returncode}


def process(api, activated, state_path, clock=None, execute_job=execute):
    clock = clock or now()
    state = read(state_path) if state_path.exists() else {'jobs': {}, 'dirty': True}
    # A crash after claiming a job must never cause another upload of that job.
    for record in state['jobs'].values():
        if record['state'] == 'started':
            record.update(state='needs_review', reason='Worker interrupted; check YouTube Studio before any retry')
            state['dirty'] = True
    if state['dirty']:
        write(state_path, state)
        api.publish(state)
        state['dirty'] = False
        write(state_path, state)
    document, _ = api.get(QUEUE)
    jobs = document.get('jobs') if isinstance(document, dict) else None
    if document.get('version') != 1 or not isinstance(jobs, list) or len(jobs) > 50:
        raise ValueError('Invalid queue schema')
    for job in jobs:
        if not valid_job(job, activated, clock) or job['id'] in state['jobs']:
            continue
        recent = sum(r.get('action') == 'generate_upload' and stamp(r['started_at']) > clock - timedelta(hours=24)
                     for r in state['jobs'].values())
        if job['action'] == 'generate_upload':
            if recent >= 6:
                continue
            # Wait for a scheduled run already holding the production lock.
            try:
                with FileLock(str(DATA / 'runner.lock'), timeout=0):
                    pass
            except Timeout:
                continue
        record = {'state': 'started', 'action': job['action'], 'started_at': clock.isoformat()}
        state['jobs'][job['id']] = record
        state['dirty'] = True
        write(state_path, state)  # Durable claim before any paid work or upload.
        try:
            # Require a confirmed status write before starting generation.
            api.publish(state)
        except Exception:
            record.update(state='held', reason='Could not report job start; no generation attempted')
            write(state_path, state)
            raise
        try:
            record.update(execute_job(job))
        except Exception:
            record.update(state='needs_review', reason='Worker stopped; inspect local log and YouTube Studio')
        record['finished_at'] = now().isoformat()
        write(state_path, state)
        api.publish(state)
        state['dirty'] = False
        write(state_path, state)
        break  # At most one job per poll.


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    settings = read(DATA / 'bridge-config.json')
    api = GitHub(token())
    with FileLock(str(DATA / 'bridge.lock'), timeout=0):
        if args.verify:
            queue, _ = api.get(QUEUE)
            if queue.get('version') != 1:
                raise ValueError('Unsupported queue version')
            state_path = DATA / 'bridge-state.json'
            state = read(state_path) if state_path.exists() else {'jobs': {}, 'dirty': True}
            api.publish(state)
            print('GitHub read/write connection verified. No video generated.')
        else:
            process(api, stamp(settings['activated_at']), DATA / 'bridge-state.json')


if __name__ == '__main__':
    try:
        main()
    except Timeout:
        pass
    except Exception as exc:
        # Do not log exception bodies: HTTP errors may contain sensitive details.
        DATA.mkdir(exist_ok=True)
        (DATA / 'bridge-error.log').write_text(now().isoformat() + ' ' + type(exc).__name__ + '\n', encoding='utf-8')
        print('Bridge stopped:', type(exc).__name__, '- verify internet and GitHub token permissions/expiry.')
        sys.exit(1)
