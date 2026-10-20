"""Offline backup and integrity checks. Run while the single worker is stopped."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from .store import Repository
from .word_export import SOURCES


def verify(repo, directory):
    issues = []
    sources = repo.list('source')
    expected = set()
    for source in sources:
        name = source['id'] + source['extension']
        expected.add(name)
        path = directory / name
        if not path.is_file():
            issues.append({'id': source['id'], 'problem': 'missing'})
        elif source.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            issues.append({'id': source['id'], 'problem': 'checksum'})
    orphans = [path.name for path in directory.iterdir() if path.is_file() and path.name not in expected] if directory.exists() else []
    with repo.connect() as db:
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    return {'integrity': integrity, 'issues': issues, 'unreferenced_files': orphans, 'sources': len(sources)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'backup', 'restore'])
    parser.add_argument('directory', nargs='?', type=Path)
    args = parser.parse_args()
    repo = Repository()
    if args.action == 'verify':
        result = verify(repo, SOURCES)
    elif args.action == 'backup':
        if not args.directory:
            parser.error('backup requires an empty destination directory')
        args.directory.mkdir(parents=True, exist_ok=False)
        result = verify(repo, SOURCES)
        if result['issues'] or result['integrity'] != 'ok':
            raise SystemExit(json.dumps(result, ensure_ascii=False))
        with repo.connect() as source, sqlite3.connect(args.directory / 'lexis.db') as target:
            source.backup(target)
        shutil.copytree(SOURCES, args.directory / 'sources') if SOURCES.exists() else (args.directory / 'sources').mkdir()
        result = verify(Repository(args.directory / 'lexis.db'), args.directory / 'sources')
        (args.directory / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        if not args.directory or not (args.directory / 'lexis.db').is_file():
            parser.error('restore requires a valid backup directory')
        result = verify(Repository(args.directory / 'lexis.db'), args.directory / 'sources')
        if result['issues'] or result['integrity'] != 'ok':
            raise SystemExit(json.dumps(result, ensure_ascii=False))
        # Never overwrite an existing workspace. Restore to a fresh data root.
        with repo.connect() as db:
            if db.execute('SELECT 1 FROM objects LIMIT 1').fetchone():
                raise SystemExit('Restore requires an empty data root; set LEXIS_DATA_DIR to a new directory.')
        if SOURCES.exists() and any(SOURCES.iterdir()):
            raise SystemExit('Restore requires an empty source directory.')
        with sqlite3.connect(args.directory / 'lexis.db') as source, repo.connect() as target:
            source.backup(target)
        shutil.copytree(args.directory / 'sources', SOURCES, dirs_exist_ok=True)
        result = verify(repo, SOURCES)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['issues'] or result['integrity'] != 'ok':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
