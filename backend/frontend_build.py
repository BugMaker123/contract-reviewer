"""Build the browser app on first start, or after frontend source changes."""
import hashlib
import shutil
import subprocess
from pathlib import Path

FRONTEND = Path(__file__).parent.parent / 'frontend'


def ensure_frontend_build():
    target = FRONTEND / 'dist' / 'index.html'
    sources = [*FRONTEND.glob('*.json'), FRONTEND / 'index.html', FRONTEND / 'vite.config.js',
               *(path for path in (FRONTEND / 'src').rglob('*') if path.is_file())]
    if target.is_file() and all(path.stat().st_mtime <= target.stat().st_mtime for path in sources):
        return
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not npm:
        raise RuntimeError('构建前端需要 Node.js 和 npm，请安装后重新运行 run.py')
    lock_digest = hashlib.sha256((FRONTEND / 'package-lock.json').read_bytes()).hexdigest()
    stamp = FRONTEND / 'node_modules' / '.lexis-lock'
    if not (FRONTEND / 'node_modules' / 'vite').is_dir() or not stamp.is_file() or stamp.read_text() != lock_digest:
        subprocess.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=FRONTEND, check=True)
        stamp.write_text(lock_digest)
    subprocess.run([npm, 'run', 'build'], cwd=FRONTEND, check=True)
