"""One-time editor update from the extracted release; preserves credentials."""
import sys
import shutil
import py_compile
from pathlib import Path
from datetime import datetime
from filelock import FileLock, Timeout

root = Path(sys.argv[1]).resolve()
source = Path(__file__).resolve().parent / 'automation.py'
try:
    if not (root / 'automation.py').is_file():
        raise ValueError('Existing GTA Craze installation was not found.')
    with FileLock(str(root / 'data' / 'runner.lock'), timeout=0):
        footage = source.parent / 'auto_footage.py'
        py_compile.compile(str(footage), doraise=True)
        if footage.resolve() != (root / 'auto_footage.py').resolve():
            shutil.copy2(footage, root / 'auto_footage.py')
        module = source.parent / 'montage.py'
        py_compile.compile(str(module), doraise=True)
        py_compile.compile(str(source), doraise=True)
        if module.resolve() != (root / 'montage.py').resolve():
            shutil.copy2(module, root / 'montage.py')
        backup = root / 'data' / ('automation-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.py')
        shutil.copy2(root / 'automation.py', backup)
        if source.resolve() != (root / 'automation.py').resolve():
            temporary = root / 'automation-update.tmp'
            shutil.copy2(source, temporary)
            temporary.replace(root / 'automation.py')
    print('EDITOR UPDATED: multi-source moving montages, portrait footage and audio-timed captions.')
except Timeout:
    print('A video is running. Wait until it finishes, then double-click this updater again.')
    sys.exit(1)
except Exception as exc:
    print('Update did not complete:', type(exc).__name__, str(exc))
    sys.exit(1)
