"""Offline web administration: initialize, backup, restore and verify.

Load the selected environment before importing the repository. Backups include
all database tables and source files; encryption keys are managed separately.
"""
import argparse
import getpass
import hashlib
import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv


def backup(repo, sources, destination):
    from sqlalchemy import MetaData, select
    from .data_maintenance import verify
    result=verify(repo,sources)
    if result['issues'] or result['integrity']!='ok':
        raise ValueError('Backup aborted: source integrity verification failed')
    destination.mkdir(parents=True,exist_ok=False)
    schema=MetaData()
    schema.reflect(repo.database.engine)
    try:
        with repo.database.engine.connect() as db:
            if repo.is_mysql:
                db=db.execution_options(isolation_level='REPEATABLE READ')
            with db.begin():
                if repo.is_mysql:
                    db.exec_driver_sql('START TRANSACTION WITH CONSISTENT SNAPSHOT')
                data={table.name:[dict(row) for row in db.execute(select(table)).mappings()]
                      for table in schema.sorted_tables}
        (destination/'database.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        if sources.exists():
            shutil.copytree(sources,destination/'sources')
        else:
            (destination/'sources').mkdir()
        hashes={str(path.relative_to(destination)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest()
                for path in destination.rglob('*') if path.is_file()}
        manifest={'format':1,'tables':{name:len(rows) for name,rows in data.items()},'sha256':hashes}
        (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        return manifest
    except BaseException:
        # A failed destination is left for diagnosis, never reported as valid.
        (destination/'FAILED').write_text('Backup incomplete',encoding='utf-8')
        raise


def restore(repo,sources,directory):
    from sqlalchemy import MetaData,select,insert,delete
    from .data_maintenance import verify
    if (directory/'FAILED').exists():
        raise ValueError('Backup is incomplete')
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format')!=1:
        raise ValueError('Unsupported backup format')
    for filename,checksum in manifest['sha256'].items():
        path=(directory/filename).resolve()
        if not path.is_relative_to(directory.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
            raise ValueError('Backup checksum mismatch')
    data=json.loads((directory/'database.json').read_text(encoding='utf-8'))
    schema=MetaData()
    schema.reflect(repo.database.engine)
    if not set(data).issubset(schema.tables):
        raise ValueError('Backup schema is newer than the target')
    if sources.exists() and any(sources.iterdir()):
        raise ValueError('Restore requires an empty source directory')
    copied=False
    try:
        with repo.database.engine.begin() as db:
            for table in schema.sorted_tables:
                if table.name not in ('schema_migrations','repository_lock') and db.execute(select(table).limit(1)).first():
                    raise ValueError('Restore requires an empty database')
            shutil.copytree(directory/'sources',sources,dirs_exist_ok=True)
            copied=True
            for table in schema.sorted_tables:
                if table.name not in data or table.name in ('schema_migrations','repository_lock'):
                    continue
                rows=data[table.name]
                if len(rows)!=manifest['tables'][table.name]:
                    raise ValueError('Backup row count mismatch')
                db.execute(delete(table))
                if rows:
                    db.execute(insert(table),rows)
    except BaseException:
        if copied:
            # Only files copied into this previously empty destination.
            for path in sources.iterdir():
                if path.is_file():
                    path.unlink()
        raise
    return verify(repo,sources)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env',type=Path,default=Path('.env.web'))
    parser.add_argument('action',choices=['init','verify','backup','restore'])
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--username',default='admin')
    parser.add_argument('--name',default='系统管理员')
    args=parser.parse_args()
    load_dotenv(args.env,override=True)
    from .store import Repository
    from .security import Security
    from .word_export import SOURCES
    from .data_maintenance import verify
    repo=Repository()
    Security(repo)
    if args.action=='init':
        password=getpass.getpass('Initial administrator password (12+ characters): ')
        result={'admin_id':Security(repo).bootstrap(args.username,args.name,password)}
    elif args.action=='verify':
        result=verify(repo,SOURCES)
    else:
        if not args.directory:
            parser.error('--directory is required')
        result=backup(repo,SOURCES,args.directory) if args.action=='backup' else restore(repo,SOURCES,args.directory)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
