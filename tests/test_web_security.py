import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update, insert, select
from backend import main
from backend.security import Security, users, user_roles, hasher, actor, PERMISSIONS


@pytest.fixture
def accounts(monkeypatch):
    import os
    if os.environ.get('LEXIS_TEST_MYSQL_URL'):
        from backend.store import Repository
        from backend import workspace_api
        from backend.security import metadata
        repo=Repository(url=os.environ['LEXIS_TEST_MYSQL_URL'])
        assert repo.database.engine.url.database.endswith('_test')
        service=Security(repo)
        with service.engine.begin() as db:
            for table in reversed(metadata.sorted_tables):
                db.execute(table.delete())
        with repo.connect() as db:
            db.execute('DELETE FROM review_events')
            db.execute('DELETE FROM objects')
        monkeypatch.setattr(main,'repository',repo)
        monkeypatch.setattr(workspace_api,'repo',repo)
    monkeypatch.setenv('LEXIS_WEB_MODE','1')
    monkeypatch.setenv('LEXIS_COOKIE_SECURE','0')
    service=Security(main.repository)
    admin=service.bootstrap('admin','管理员','initial-admin-password')
    with service.engine.begin() as db:
        db.execute(update(users).values(must_change_password=False))
        for name in ('alice','bob'):
            db.execute(insert(users).values(id=name,username=name,name=name,password_hash=hasher.hash('personal-password-'+name),active=True,must_change_password=False))
            db.execute(insert(user_roles).values(user_id=name,role_id='legal'))
    return service,admin


def login(client,name='alice',password=None):
    response=client.post('/api/auth/login',json={'username':name,'password':password or 'personal-password-'+name})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=client.cookies.get('lexis_csrf')
    return response


def test_login_csrf_isolation_and_revocation(accounts):
    service,_=accounts
    with TestClient(main.app) as alice,TestClient(main.app) as bob:
        assert alice.get('/api/tasks').status_code==401
        login(alice);login(bob,'bob')
        task=alice.post('/api/tasks',json={'title':'私人合同','text':'双方约定付款期限为三十日。'}).json()
        assert 'id' in task,task
        assert bob.get('/api/tasks/'+task['id']).status_code==404
        assert bob.get('/api/tasks').json()['total']==0
        assert alice.get('/api/tasks').json()['total']==1
        assert alice.get('/api/admin/users').status_code==403
        alice.headers.pop('X-CSRF-Token')
        assert alice.post('/api/tasks',json={'title':'无凭据','text':'合同正文'}).status_code==403
        with service.engine.begin() as db:
            db.execute(update(users).where(users.c.id=='bob').values(active=False))
        assert bob.get('/api/tasks').status_code==401


def test_password_reset_requires_change_and_revokes_all_sessions(accounts):
    service,admin=accounts
    with TestClient(main.app) as client:
        login(client,'admin','initial-admin-password')
        response=client.put('/api/admin/users/alice',json={'username':'alice','name':'Alice','role_ids':['legal'],'active':True,'password':'reset-personal-password'})
        assert response.status_code==200,response.text
        with TestClient(main.app) as alice:
            assert login(alice,'alice','reset-personal-password').json()['must_change_password']
            assert alice.get('/api/tasks').status_code==403
            assert alice.post('/api/auth/password',json={'current_password':'reset-personal-password','new_password':'changed-personal-password'}).status_code==200
            assert alice.get('/api/tasks').status_code==401


def test_source_and_work_copy_cannot_be_used_by_other_user(accounts):
    with TestClient(main.app) as alice,TestClient(main.app) as bob:
        login(alice);login(bob,'bob')
        source=alice.post('/api/contracts/import',files={'file':('a.txt',b'private contract')}).json()
        assert 'source_id' in source,source
        for suffix in ('','/file','?include_text=true'):
            assert bob.get('/api/sources/'+source['source_id']+suffix).status_code==404
        response=bob.post('/api/tasks',json={'title':'越权引用','text':'正文','source_id':source['source_id']})
        assert response.status_code==404


def test_published_checklists_only_visible_to_legal(accounts):
    service,admin=accounts
    with TestClient(main.app) as manager,TestClient(main.app) as alice:
        login(manager,'admin','initial-admin-password');login(alice)
        category=manager.post('/api/categories',json={'name':'采购','code':'PUR'}).json()
        body={'name':'内部清单','category_id':category['id'],'items':[{'id':'one','title':'付款','requirement':'付款期限明确'}],'published':False}
        checklist=manager.post('/api/checklists',json=body).json()
        assert 'id' in checklist,checklist
        assert alice.get('/api/checklists/'+checklist['id']).status_code==404
        assert alice.get('/api/checklists?summary=true').json()['items']==[]
        assert alice.put('/api/checklists/'+checklist['id'],json={**body,'revision':1}).status_code==403


def test_work_copy_survives_new_session_and_conflicts(accounts):
    with TestClient(main.app) as alice,TestClient(main.app) as bob:
        login(alice);login(bob,'bob')
        body={'key':'review-new','payload':{'text':'服务端保存的合同正文'}}
        created=alice.post('/api/work-copies',json=body)
        assert created.status_code==200,created.text
        record=created.json()
        assert bob.get('/api/work-copies/'+record['id']).status_code==404
        assert alice.put('/api/work-copies/'+record['id'],json={**body,'revision':1}).status_code==200
        assert alice.put('/api/work-copies/'+record['id'],json={**body,'revision':1}).status_code==409
        alice.post('/api/auth/logout')
        alice.cookies.clear()
        login(alice)
        assert alice.get('/api/work-copies?key=review-new').json()['items'][0]['payload']==body['payload']


def test_model_configuration_is_encrypted_and_never_returned(accounts,monkeypatch):
    from cryptography.fernet import Fernet
    from backend.security import settings
    monkeypatch.setenv('LEXIS_MODEL_ENCRYPTION_KEY',Fernet.generate_key().decode())
    with TestClient(main.app) as manager,TestClient(main.app) as alice:
        login(manager,'admin','initial-admin-password');login(alice)
        body={'model_name':'approved-model','base_url':'https://api.deepseek.com/v1','api_key':'secret-credential'}
        response=manager.put('/api/admin/model',json=body)
        assert response.status_code==200,response.text
        assert response.json()['has_api_key']
        assert 'secret-credential' not in response.text and 'encrypted_key' not in response.text
        with accounts[0].engine.connect() as db:
            assert 'secret-credential' not in db.execute(select(settings.c.data)).scalar()
        assert alice.get('/api/admin/model').status_code==403
        assert manager.put('/api/admin/model',json={**body,'base_url':'http://unapproved.example/v1'}).status_code==422


def test_two_users_queue_promotes_with_original_owner_and_survives_disconnect(accounts,monkeypatch):
    import asyncio
    from backend import review_jobs
    monkeypatch.setenv('LEXIS_REVIEW_CONCURRENCY','1')
    monkeypatch.setenv('LEXIS_REVIEW_PER_MODEL','1')
    repo=main.repository
    service=accounts[0]
    async def scenario():
        gate=asyncio.Event();entered=[];jobs=[];runs=[]
        async def events(snapshot,config):
            entered.append(snapshot['title'])
            if snapshot['title']=='alice':
                await gate.wait()
            yield 'complete',{'issues':[],'segments':[],'summary':{'verdict':'通过'}}
        try:
            for name in ('alice','bob'):
                with service.engine.connect() as db:
                    current=service.identity(db,name)
                token=actor.set(current)
                try:
                    task=repo.create('task',{'title':name,'text':'双方约定验收后付款。','status':'draft'})
                    run=repo.start_run(task['id']);runs.append(run)
                    jobs.append(review_jobs.launch(repo,run,{},events))
                finally:
                    actor.reset(token)
            await asyncio.sleep(.05)
            assert entered==['alice']
            assert repo.get(runs[1]['id'])['status']=='queued'
            # Queries and saves remain available while the model is waiting.
            repo.create('contract_draft',{'title':'同时保存','text':'草稿正文'})
            assert repo.get(runs[0]['id'])['status']=='running'
            gate.set()
            await asyncio.wait_for(asyncio.gather(*(job.task for job in jobs)),5)
            assert entered==['alice','bob']
            assert all(repo.get(run['id'])['status']=='completed' for run in runs)
            with service.engine.connect() as db:
                token=actor.set(service.identity(db,'bob'))
            try:
                assert repo.get(runs[1]['id'])['status']=='completed'
                from fastapi import HTTPException
                with pytest.raises(HTTPException):
                    repo.get(runs[0]['id'])
            finally:
                actor.reset(token)
        finally:
            gate.set();await review_jobs.shutdown(repo)
    asyncio.run(scenario())


def test_admin_pagination_filters_and_deletion(accounts):
    service,admin=accounts
    with TestClient(main.app) as client:
        login(client,'admin','initial-admin-password')
        first=client.get('/api/admin/users?page=1&page_size=2').json()
        second=client.get('/api/admin/users?page=2&page_size=2').json()
        assert first['total']==3 and len(first['items'])==2
        assert not {u['id'] for u in first['items']} & {u['id'] for u in second['items']}
        assert client.get('/api/admin/users?q=alice&page=1').json()['items'][0]['username']=='alice'
        assert client.get('/api/admin/users?q=%25&page=1').json()['total']==0
        assert client.get('/api/admin/users?status=inactive&page=1').json()['total']==0
        assert client.get('/api/admin/users?page=0').status_code==422
        assert client.get('/api/admin/roles?page_size=101').status_code==422
        assert client.delete('/api/admin/users/'+admin).status_code==409
        assert client.delete('/api/admin/roles/administrator').status_code==409
        assert client.delete('/api/admin/roles/legal').status_code==409
        role=client.post('/api/admin/roles',json={'name':'临时角色','description':'用于查询','permissions':['review.view']}).json()['id']
        filtered=client.get('/api/admin/roles?q=临时&page=1&page_size=1').json()
        assert filtered['total']==1 and filtered['items'][0]['id']==role
        assert client.get('/api/admin/roles?page=1&page_size=1').json()['total']==3
        assert client.put('/api/admin/roles/'+role,json={'name':'更新角色','description':'更新说明','permissions':['review.view','review.create']}).status_code==200
        assert client.delete('/api/admin/roles/'+role).status_code==200
        assert client.delete('/api/admin/roles/'+role).status_code==404
        with TestClient(main.app) as alice:
            login(alice)
            assert alice.delete('/api/admin/users/bob').status_code==403
            assert client.delete('/api/admin/users/alice').status_code==200
            assert alice.get('/api/auth/me').status_code==401
        assert client.get('/api/admin/users?page=1').json()['total']==2
        with service.engine.connect() as db:
            assert not db.execute(select(user_roles).where(user_roles.c.user_id=='alice')).first()


def test_model_history_restore_and_connection_test(accounts,monkeypatch):
    import httpx
    from cryptography.fernet import Fernet
    from backend import model_settings
    from backend.security import model_history
    monkeypatch.setenv('LEXIS_MODEL_ENCRYPTION_KEY',Fernet.generate_key().decode())
    calls=[]
    outcome={'status':200}
    class ModelClient:
        def __init__(self,**kwargs):
            assert kwargs['follow_redirects'] is False
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,headers,json):
            calls.append({'url':url,'headers':headers,'json':json})
            if outcome['status']=='timeout':
                raise httpx.ReadTimeout('contains-secret-credential')
            return httpx.Response(outcome['status'],json={'choices':[{'message':{'content':'OK'}}]})
    monkeypatch.setattr(model_settings.httpx,'AsyncClient',ModelClient)
    with TestClient(main.app) as client,TestClient(main.app) as alice:
        login(client,'admin','initial-admin-password');login(alice)
        first={'model_name':'model-a','base_url':'https://api.deepseek.com/v1','api_key':'first-secret','max_retries':2}
        assert client.put('/api/admin/model',json=first).status_code==200
        old=client.get('/api/admin/model/history').json()['items'][0]
        assert old['operator']=='管理员' and old['has_api_key']
        second={**first,'model_name':'model-b','api_key':'second-secret'}
        assert client.put('/api/admin/model',json=second).status_code==200
        history=client.get('/api/admin/model/history?page=1&page_size=1').json()
        assert history['total']==2 and len(history['items'])==1
        assert client.get('/api/admin/model/history?page=2&page_size=1').json()['items'][0]['id']==old['id']
        assert 'secret' not in str(history) and 'encrypted_key' not in str(history)
        restored=client.post('/api/admin/model/history/'+old['id']+'/restore')
        assert restored.status_code==200 and restored.json()['model_name']=='model-a'
        assert model_settings.load_model(secret=True)['api_key']=='first-secret'
        assert client.get('/api/admin/model/history').json()['items'][0]['action']=='restore'
        assert client.get('/api/admin/model/history').json()['total']==3
        test_body={**first,'model_name':'unsaved-model','api_key':''}
        result=client.post('/api/admin/model/test',json=test_body)
        assert result.status_code==200 and result.json()['success'] and result.json()['latency_ms']>=0
        assert calls[-1]['headers']['Authorization']=='Bearer first-secret'
        assert calls[-1]['json']['model']=='unsaved-model'
        assert model_settings.load_model()['model_name']=='model-a'
        assert client.get('/api/admin/model/history').json()['total']==3
        test_body['api_key']='unsaved-secret'
        client.post('/api/admin/model/test',json=test_body)
        assert calls[-1]['headers']['Authorization']=='Bearer unsaved-secret'
        for status in (401,404,429,500,'timeout'):
            outcome['status']=status
            response=client.post('/api/admin/model/test',json=test_body)
            assert response.status_code==200 and response.json()['success'] is False
            assert 'secret' not in response.text
        assert client.post('/api/admin/model/test',json={**test_body,'base_url':'http://unapproved.example'}).status_code==422
        assert client.post('/api/admin/model/history/missing/restore').status_code==404
        assert alice.get('/api/admin/model/history').status_code==403
        assert alice.post('/api/admin/model/test',json=first).status_code==403
        assert alice.post('/api/admin/model/history/'+old['id']+'/restore').status_code==403
        with accounts[0].engine.connect() as db:
            for raw in db.execute(select(model_history.c.data)).scalars():
                assert 'first-secret' not in raw and 'second-secret' not in raw
