"""Serve the built Vue SPA for all browser routes."""
from pathlib import Path

from fastapi import HTTPException

FRONTEND = Path(__file__).parent.parent / 'frontend'
DIST = FRONTEND / 'dist'
PORTAL_PAGES = {'/': 'start', '/records': 'records', '/categories': 'categories', '/checklists': 'checklists'}


def render_portal(path: str = '/') -> str:
    index = DIST / 'index.html'
    if not index.is_file():
        raise HTTPException(503, '前端尚未构建，请在 frontend 目录执行 npm ci 和 npm run build，或运行 python run.py')
    return index.read_text(encoding='utf-8')


def render_workbench() -> str:
    return render_portal()
