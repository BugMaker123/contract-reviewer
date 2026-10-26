"""Offline SQLite -> MySQL import. Never modifies the source database/files."""
import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path



def migrate(source_db, source_files, target, target_files, owner):
    if not owner.strip():
        raise ValueError('An explicit legacy owner is required')
    if source_files.resolve() == target_files.resolve():
        raise ValueError('Source and target file directories must differ')
    # Read-only SQLite URI also prevents accidentally creating a missing source.
    with sqlite3.connect(source_db.resolve().as_uri() + '?mode=ro', uri=True) as old:
        old.row_factory = sqlite3.Row
        if old.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Source database failed integrity check')
        objects = old.execute('SELECT * FROM objects').fetchall()
        events = old.execute('SELECT * FROM review_events ORDER BY id').fetchall()
    public = {'category', 'checklist', 'checklist_version', 'template_group', 'contract_template', 'template_release'}
    ids = {row['id'] for row in objects}
    files = []
    historical_orphans=[]
    for row in objects:
        if row['parent'] and row['parent'] not in ids:
            if row['kind'] in ('template_release','template_validation','checklist_version'):
                historical_orphans.append({'id':row['id'],'kind':row['kind'],'parent':row['parent']})
            else:
                raise ValueError('Dangling parent: ' + row['id'])
        if row['kind'] == 'source':
            data = json.loads(row['data'])
            filename = row['id'] + data['extension']
            if Path(filename).name != filename:
                raise ValueError('Invalid source filename')
            path = source_files / filename
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if data.get('sha256') and digest != data['sha256']:
                raise ValueError('Source checksum mismatch: ' + filename)
            files.append((path, filename, digest))
    if any(row['run_id'] not in ids for row in events):
        raise ValueError('Dangling review event')
    if target_files.exists() and any(target_files.iterdir()):
        raise ValueError('Target source directory must be empty')
    target_files.mkdir(parents=True, exist_ok=True)
    copied = []
    try:
        with target.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM objects LIMIT 1').fetchone():
                raise ValueError('Target database must be empty')
            for source, filename, digest in files:
                destination = target_files / filename
                shutil.copy2(source, destination)
                copied.append(destination)
                if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                    raise ValueError('Copied file checksum mismatch: ' + filename)
            for row in objects:
                db.execute('INSERT INTO objects(id,kind,parent,data,revision,created,updated,owner_user_id,created_by,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?)',
                           (*[row[key] for key in ('id', 'kind', 'parent', 'data', 'revision', 'created', 'updated')],
                            None if row['kind'] in public else owner, owner, owner))
            for row in events:
                db.execute('INSERT INTO review_events(id,run_id,data) VALUES(?,?,?)', (row['id'], row['run_id'], row['data']))
            if db.execute('SELECT count(*) FROM objects').fetchone()[0] != len(objects):
                raise ValueError('Object count mismatch')
            if db.execute('SELECT count(*) FROM review_events').fetchone()[0] != len(events):
                raise ValueError('Event count mismatch')
    except BaseException:
        for path in copied:
            path.unlink(missing_ok=True)
        raise
    return {'objects': len(objects), 'review_events': len(events), 'files': len(files),
            'historical_orphans':historical_orphans,
            'owner_user_id': owner, 'file_hashes': {name: digest for _, name, digest in files}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path, required=True)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--target-sources', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--env',type=Path,default=Path('.env.web'))
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(args.env,override=True)
    from .store import Repository
    target = Repository()
    if not target.is_mysql:
        parser.error('Set LEXIS_DATABASE_URL to a MySQL target')
    from .security import Security,users
    from sqlalchemy import select
    with Security(target).engine.connect() as db:
        if not db.execute(select(users.c.id).where(users.c.id==args.owner)).first():
            parser.error('--owner must identify an initialized account')
    report = migrate(args.sqlite, args.sources, target, args.target_sources, args.owner)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
