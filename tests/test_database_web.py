"""Exercise the production SQL dialect when LEXIS_TEST_MYSQL_URL is supplied."""
import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from backend.store import Repository
from backend.migrate_data import migrate


@pytest.fixture
def mysql_repo():
    url = os.environ.get('LEXIS_TEST_MYSQL_URL')
    if not url:
        pytest.skip('LEXIS_TEST_MYSQL_URL is not configured')
    repo = Repository(url=url)
    # Only an explicitly named scratch database may be cleared.
    assert repo.database.engine.url.database.endswith('_test')
    with repo.connect() as db:
        db.execute('DELETE FROM review_events')
        db.execute('DELETE FROM objects')
    yield repo
    repo.database.engine.dispose()


def test_mysql_catalog_json_and_transactions(mysql_repo):
    repo = mysql_repo
    category = repo.create('category',{'name':'采购','code':'PUR'})
    checklist = repo.create('checklist',{'name':'清单','category_id':category['id'],
        'published':True,'archived':False,'version':1,'items':[{'title':'付款','requirement':'期限明确'}]})
    page = repo.catalog_page('checklist',1,10,search='付款',published=True,archived=False)
    assert page['total'] == 1
    assert page['items'][0]['item_count'] == 1
    assert repo.catalog_page('category',1,10)['items'][0]['checklist_count'] == 1
    changed = repo.update(checklist['id'],{'version':2},1)
    assert changed['revision'] == 2
    with pytest.raises(HTTPException):
        repo.update(checklist['id'],{'version':3},1)
    assert len(repo.list('checklist_version',checklist['id'])) == 1
    with pytest.raises(HTTPException):
        repo.delete_catalog(category['id'],'category',1)
    with pytest.raises(RuntimeError):
        with repo.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM objects WHERE id=?',(checklist['id'],))
            raise RuntimeError('rollback')
    assert repo.get(checklist['id'])['revision'] == 2


def test_mysql_parallel_claim_and_history(mysql_repo):
    repo = mysql_repo
    task = repo.create('task',{'title':'合同','text':'合同正文','status':'draft','archived':False,'active_run':None})
    def start(_):
        try:
            return repo.start_run(task['id'])
        except HTTPException as error:
            assert error.status_code == 409
    with ThreadPoolExecutor(max_workers=4) as pool:
        runs = [r for r in pool.map(start,range(4)) if r]
    assert len(runs) == 1
    run = runs[0]
    assert repo.task_page(archived=False)['total'] == 1
    assert repo.run_summaries(task['id'])[0]['number'] == 1
    for index in range(260):
        repo.append_trace(run['id'],{'index':index})
    with repo.connect() as db:
        assert db.execute('SELECT count(*) FROM review_events').fetchone()[0] == 256
    repo.interrupt_running()
    assert repo.get(task['id'])['status'] == 'interrupted'
    assert repo.get(run['id'])['status'] == 'interrupted'


def test_sqlite_migration_preserves_both_draft_kinds_and_files(mysql_repo,tmp_path):
    from backend.source_storage import save_source
    old = Repository(tmp_path/'old.db')
    sources = tmp_path/'old-sources'
    source = save_source(old,sources,{'extension':'.txt','name':'合同.txt'},b'contract')
    old.create('draft',{'title':'历史起草'})
    draft = old.create('contract_draft',{'title':'当前起草','source_id':source['id']})
    old.update(draft['id'],{'text':'保留版本'},1)
    result = migrate(tmp_path/'old.db',sources,mysql_repo,tmp_path/'new-sources','legacy-admin')
    assert result['objects'] == 3 and result['files'] == 1
    assert mysql_repo.get(draft['id']) == old.get(draft['id'])
    assert len(mysql_repo.list('draft')) == 1
    with pytest.raises(ValueError):
        migrate(tmp_path/'old.db',sources,mysql_repo,tmp_path/'other-sources','legacy-admin')


def test_mysql_backup_restore_opens_contract_and_exports(mysql_repo,tmp_path,monkeypatch):
    from backend import main,workspace_api,word_export
    from backend.security import Security,metadata,users,user_roles
    from backend.source_storage import save_source
    from backend.web_admin import backup,restore
    from sqlalchemy import update,select
    from fastapi.testclient import TestClient
    from docx import Document
    from io import BytesIO
    repo=mysql_repo
    service=Security(repo)
    with service.engine.begin() as db:
        for table in reversed(metadata.sorted_tables):
            db.execute(table.delete())
    admin=service.bootstrap('restore-admin','恢复演练管理员','restore-initial-password')
    with service.engine.begin() as db:
        db.execute(update(users).values(must_change_password=False))
    sources=tmp_path/'original-sources'
    source=save_source(repo,sources,{'extension':'.txt','name':'合同.txt','text':'双方约定付款期限三十日。'},'双方约定付款期限三十日。'.encode())
    task=repo.create('task',{'title':'恢复合同','text':'双方约定付款期限三十日。','type':'采购合同','role':'中立审慎','mode':'deep','status':'draft','source_id':source['id'],'archived':False})
    run=repo.start_run(task['id'])
    repo.update_review(run['id'],{'status':'completed','result':{'issues':[],'segments':[],'summary':{'verdict':'通过'}}},task_changes={'status':'completed','active_run':run['id']})
    directory=tmp_path/'backup'
    manifest=backup(repo,sources,directory)
    with repo.connect() as db:
        db.execute('DELETE FROM review_events');db.execute('DELETE FROM objects')
    with service.engine.begin() as db:
        for table in reversed(metadata.sorted_tables):
            db.execute(table.delete())
    restored=tmp_path/'restored-sources'
    result=restore(repo,restored,directory)
    assert result['integrity']=='ok' and not result['issues']
    assert repo.get(task['id'])['title']=='恢复合同'
    assert (restored/(source['id']+'.txt')).read_bytes()==(sources/(source['id']+'.txt')).read_bytes()
    monkeypatch.setattr(main,'repository',repo);monkeypatch.setattr(workspace_api,'repo',repo)
    monkeypatch.setattr(main,'SOURCES',restored);monkeypatch.setattr(word_export,'SOURCES',restored)
    monkeypatch.setenv('LEXIS_WEB_MODE','1');monkeypatch.setenv('LEXIS_COOKIE_SECURE','0')
    with TestClient(main.app) as client:
        response=client.post('/api/auth/login',json={'username':'restore-admin','password':'restore-initial-password'})
        assert response.status_code==200
        assert client.get('/api/tasks/'+task['id']).status_code==200
        response=client.get('/api/runs/'+run['id']+'/export?scope=current')
        assert response.status_code==200,response.text
        assert '三十日' in '\n'.join(p.text for p in Document(BytesIO(response.content)).paragraphs)
