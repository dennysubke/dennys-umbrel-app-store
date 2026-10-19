"""Run as root on the disposable runner; verify narrowly scoped storage setup."""
import os
from pathlib import Path
import stat
import subprocess
import tempfile

hook = Path('denny-moinpdf/hooks/pre-start').resolve()
assert os.geteuid() == 0, 'This fixture requires disposable-runner root privileges'
assert os.access(hook, os.X_OK), 'Umbrel only executes executable lifecycle hooks'
assert b'\r' not in hook.read_bytes(), 'The Linux hook must use LF line endings'

with tempfile.TemporaryDirectory(prefix='moinpdf-hook-') as temporary:
    root = Path(temporary)
    definition = root / 'app definition'
    definition.mkdir()
    environment = {**os.environ, 'APP_DATA_DIR': str(definition)}
    environment.pop('APP_DATA_ROOT', None)
    subprocess.run([str(hook)], env=environment, check=True)
    jobs = definition / 'data/document-jobs'
    metadata = jobs.stat()
    assert (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)) == (1000, 1000, 0o700)

    # Reproduce Docker's ownership when a new bind source was missing on update.
    relocated = root / 'relocated data'
    jobs = relocated / 'document-jobs'
    jobs.mkdir(parents=True, mode=0o755)
    existing = jobs / 'existing-result.pdf'
    existing.write_bytes(b'%PDF-synthetic-existing-result\n')
    existing.chmod(0o640)
    os.chown(existing, 1234, 1234)
    before = existing.stat()
    environment['APP_DATA_ROOT'] = str(relocated)
    for _ in range(2):
        subprocess.run([str(hook)], env=environment, check=True)
        metadata = jobs.stat()
        assert (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)) == (1000, 1000, 0o700)
        after = existing.stat()
        assert existing.read_bytes() == b'%PDF-synthetic-existing-result\n'
        assert (after.st_uid, after.st_gid, after.st_mode, after.st_ino, after.st_mtime_ns) == (
            before.st_uid, before.st_gid, before.st_mode, before.st_ino, before.st_mtime_ns)

    # A job-directory symlink must never redirect the root hook's chmod/chown.
    rejected_root = root / 'rejected'
    rejected_root.mkdir()
    target = root / 'unrelated'
    target.mkdir(mode=0o755)
    before = target.stat()
    (rejected_root / 'document-jobs').symlink_to(target, target_is_directory=True)
    environment['APP_DATA_ROOT'] = str(rejected_root)
    result = subprocess.run([str(hook)], env=environment, capture_output=True, text=True)
    assert result.returncode != 0 and 'symbolic link' in result.stderr
    after = target.stat()
    assert (after.st_uid, after.st_gid, after.st_mode) == (before.st_uid, before.st_gid, before.st_mode)

print('PASS: fresh and existing root-owned job directories, relocated storage, private permissions, unchanged existing files, idempotence and symlink refusal.')
