"""Contract review and delivery closure, using an isolated repository."""
import asyncio
from io import BytesIO
import pytest
from docx import Document
from fastapi.testclient import TestClient
from backend.main import app
from backend import graph, workspace_api, review_jobs
from backend.store import now

TEXT = '第一条 设备交付。第二条 验收后30日付款。'
REQ = {'id':'r1','text':'付款期限不超过30日','priority':'required','source':'用户要求'}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with TestClient(app) as client:
        yield client


def seed(client, requirements=None):
    task = client.post('/api/tasks', json={'title':'功能闭环合同','text':TEXT,'mode':'quick','requirements': requirements or []}).json()
    run = workspace_api.repo.start_run(task['id'])
    result = {'issues':[], 'segments':[], 'summary':{'verdict':'需要复核','risk_level':'一般','compliance_score':80},
              'coverage':'规则检查','admission':{'reason':'合同准入通过'},'requirement_findings':[]}
    run = workspace_api.repo.update(run['id'], {'status':'completed','result':result,'completed_at':now()})
    workspace_api.repo.update(task['id'], {'status':'pending_review','active_run':run['id']})
    return client.get('/api/tasks/'+task['id']).json(), run


def verify(client, run):
    return client.post('/api/runs/'+run['id']+'/verify-current',json={'revision':run['revision']})


def complete(client, task_id, confirmations=None):
    task = client.get('/api/tasks/'+task_id).json()
    return client.post('/api/tasks/'+task_id+'/complete',json={'archived':False,'revision':task['revision'],'confirmations':confirmations or {}})


def test_requirement_findings_do_not_add_a_completion_confirmation_step(client):
    task, run = seed(client,[REQ])
    assert complete(client,task['id']).status_code == 200
    saved = client.get('/api/runs/'+run['id']).json()
    assert saved.get('completion_confirmations') == {}
    assert not saved.get('current_verification')


def test_manual_issue_and_accepted_change_invalidate_current_verification(client):
    task, run = seed(client,[REQ])
    run = verify(client,run).json()
    response = client.post('/api/runs/'+run['id']+'/issues',json={'revision':run['revision'],'title':'付款期限','analysis':'需要更明确的付款安排','evidence':'验收后30日付款。','suggestion':'验收后15日付款。'})
    assert response.status_code == 200, response.text
    run = response.json(); issue = run['result']['issues'][-1]
    assert issue['source'] == 'manual'
    assert complete(client,task['id']).status_code == 409
    response = client.put('/api/runs/'+run['id']+'/handling',json={'revision':run['revision'],'applied':[issue['id']], 'decisions':{issue['id']:'applied'}})
    assert response.status_code == 200
    assert not response.json()['current_verification_valid']
    assert complete(client,task['id']).status_code == 200


def test_verification_rejects_stale_revision_and_changed_conditions(client):
    task, run = seed(client,[REQ])
    assert verify(client,run).status_code == 200
    assert verify(client,run).status_code == 409
    task = client.get('/api/tasks/'+task['id']).json()
    assert client.put('/api/tasks/'+task['id'],json={**task,'background':'交易背景已改变'}).status_code == 200
    run = client.get('/api/runs/'+run['id']).json()
    assert verify(client,run).status_code == 409
    assert complete(client,task['id']).status_code == 409


def test_requirement_conflicts_remain_visible_without_confirmation_gate(client):
    task, run = seed(client,[REQ])
    run = verify(client,run).json()
    verification = run['current_verification']
    verification['findings'][0]['conflict_with'] = ['r2']
    workspace_api.repo.update(run['id'],{'current_verification':verification})
    response = complete(client,task['id'],{'r1':'人工确认接受这一要求冲突'})
    assert response.status_code == 200
    assert workspace_api.repo.get(run['id'])['current_verification']['findings'][0]['conflict_with'] == ['r2']


def test_report_preview_and_word_share_content_and_export_options(client):
    task, run = seed(client,[REQ])
    run = client.post('/api/runs/'+run['id']+'/issues', json={'revision':run['revision'],'title':'付款期限需明确','analysis':'需要明确付款安排','evidence':'验收后30日付款。','suggestion':'验收后15日付款。','severity':'critical'}).json()
    result = run['result']
    result['tax_settlement'] = {'vat_rate':'6%','vat_rate_evaluation':'核对交易适用税率','invoice_detail':'核对发票类型','settlement_method':'银行转账'}
    result['summary']['key_dealbreakers'] = ['付款条件需确认']
    result['requirement_findings'] = [{**REQ,'status':'needs_review','explanation':'请核对付款条款','evidence':'','conflict_with':[]}]
    run = workspace_api.repo.update(run['id'], {'result': result}, run['revision'])
    run = verify(client,run).json()
    content = client.get('/api/runs/'+run['id']+'/report-content').json()['paragraphs']
    response = client.get('/api/runs/'+run['id']+'/export?scope=report')
    assert response.status_code == 200
    word = Document(BytesIO(response.content))
    assert [p['text'] for p in content] == [p.text for p in word.paragraphs if p.text]
    assert any('风险等级说明' == p['text'] for p in content)
    titles = [p['text'] for p in content]
    assert titles.index('重点要求核验（本轮原文）') < titles.index('全文审查结论')
    assert next(i for i,text in enumerate(titles) if REQ['text'] in text) < titles.index('全文审查结论')
    assert any(p['text'].startswith('严重程度：重大风险') for p in content)
    assert any(p['text'].startswith('重大风险 · 1 项') for p in content)
    assert any(p['text'].startswith('【重大风险】') for p in content)
    assert any('当前采纳稿要求核验' in p['text'] for p in content)
    assert any('税率评价：核对交易适用税率' == p['text'] for p in content)
    assert any('付款条件需确认' == p['text'] for p in content)
    for scope in ('current','tracked','all'):
        assert client.get('/api/runs/'+run['id']+'/export?scope='+scope).status_code == 409
    assert client.get('/api/runs/'+run['id']+'/export?scope=applied_report').status_code == 200
    assert client.get('/api/runs/'+run['id']+'/audit').status_code == 409
    client.put('/api/runs/'+run['id']+'/handling',json={'revision':run['revision'],'applied':[],'decisions':{issue['id']:'rejected' for issue in run['result']['issues']}})
    assert complete(client,task['id']).status_code == 200
    assert client.get('/api/runs/'+run['id']+'/audit').json()['id'] == run['id']


def test_manual_issue_rejects_bad_anchor_and_historical_run(client):
    task, run = seed(client)
    body = {'revision':run['revision'],'title':'人工意见','analysis':'需要修改','evidence':'不存在的正文'}
    assert client.post('/api/runs/'+run['id']+'/issues',json=body).status_code == 422
    new = workspace_api.repo.start_run(task['id'])
    body['evidence'] = ''
    assert client.post('/api/runs/'+run['id']+'/issues',json=body).status_code == 409


def test_background_job_survives_subscriber_disconnect(isolated_workspace):
    async def scenario():
        repo = workspace_api.repo
        task = repo.create('task',{'title':'后台任务','text':TEXT,'status':'draft','archived':False})
        run = repo.start_run(task['id']); release = asyncio.Event()
        async def events(snapshot, config):
            await release.wait()
            yield 'complete', {'issues':[], 'summary':{'verdict':'完成'}}
        job = review_jobs.launch(repo,run,{},events)
        stream = review_jobs.subscribe(repo,run['id'])
        assert 'event: init' in await anext(stream)
        await stream.aclose()
        assert not job.done and repo.get(run['id'])['status'] == 'running'
        release.set(); await job.task
        assert repo.get(run['id'])['status'] == 'completed'
        replay = ''.join([item async for item in review_jobs.subscribe(repo,run['id'])])
        assert 'event: complete' in replay
        await review_jobs.shutdown(repo)
    asyncio.run(scenario())


def test_background_cancel_preserves_previous_active_run(isolated_workspace):
    async def scenario():
        repo = workspace_api.repo
        task = repo.create('task',{'title':'取消任务','text':TEXT,'status':'draft','active_run':'previous'})
        run = repo.start_run(task['id'])
        async def events(snapshot, config):
            await asyncio.sleep(100)
            yield 'complete', {}
        job = review_jobs.launch(repo,run,{},events)
        await asyncio.sleep(0)
        await review_jobs.cancel(repo,run['id'])
        assert repo.get(run['id'])['status'] == 'interrupted'
        assert repo.get(task['id'])['active_run'] == 'previous'
        await review_jobs.shutdown(repo)
    asyncio.run(scenario())


def test_functional_workbench_in_browser(isolated_workspace, monkeypatch):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    monkeypatch.setattr(graph,'get_llm_client',lambda config:None)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1920,'height':1080})
        errors = []
        page.on('pageerror',lambda err:errors.append(str(err)))
        task = page.request.post(base+'/api/tasks',data={'title':'完整功能浏览器验收','text':TEXT,'mode':'quick','requirements':[REQ]}).json()
        page.request.post(base+'/api/tasks/'+task['id']+'/review/stream',data={})
        page.goto(base+'/workbench?task='+task['id'])
        page.locator('.wb-functional-overview > summary').click()
        priority=page.locator('.wb-functional-overview .wb-priority-review')
        expect(priority).to_be_visible()
        expect(priority).to_contain_text(REQ['text'])
        assert priority.evaluate('(el)=>el.previousElementSibling.textContent.includes("准入结论") && el.nextElementSibling.textContent.includes("审查总评")')
        expect(page.locator('#opinion-drawer .wb-priority-review')).to_have_count(0)
        page.get_by_role('button',name='＋ 添加人工意见',exact=True).click()
        page.get_by_label('意见标题',exact=True).fill('人工确认付款条件')
        page.get_by_label('风险说明',exact=True).fill('明确付款时间可减少争议')
        page.get_by_label('原文证据',exact=True).fill('验收后30日付款。')
        page.get_by_label('建议修订',exact=True).fill('验收后15日付款。')
        page.get_by_role('button',name='保存人工意见',exact=True).click()
        expect(page.get_by_text('人工确认付款条件',exact=True).first).to_be_visible()
        page.locator('.wb-export-menu > summary').click()
        expect(page.get_by_role('button',name='当前采纳稿（清洁版）',exact=True)).to_be_visible()
        with page.expect_download() as download:
            page.get_by_role('button',name='全部审查意见书',exact=True).click()
        assert download.value.suggested_filename.endswith('.docx')
        page.get_by_role('button',name='审查意见书',exact=True).click()
        expect(page.locator('#printable-report')).to_contain_text('当前采纳稿要求核验')
        expect(page.locator('#printable-report')).to_contain_text('人工确认付款条件')
        page.get_by_role('button',name='关闭意见书',exact=True).click()
        page.reload()
        expect(page.get_by_text('人工确认付款条件',exact=True).first).to_be_visible()
        saved = page.request.get(base+'/api/tasks/'+task['id']).json()['run']
        manual = next(issue for issue in saved['result']['issues'] if issue.get('source') == 'manual')
        page.locator('#card-'+manual['id']).get_by_role('button',name='采纳',exact=True).click()
        page.locator('.wb-functional-overview > summary').click()
        for issue in saved['result']['issues']:
            if issue['id'] != manual['id']:
                page.locator('#card-'+issue['id']).get_by_role('button',name='拒绝',exact=True).click()
        page.get_by_role('button',name='完成审核',exact=True).click()
        page.goto(base+'/workbench?task='+task['id'])
        expect(page.get_by_role('button',name='已完成审核',exact=True)).to_be_visible()
        page.reload()
        page.locator('.wb-functional-overview > summary').click()
        expect(page.frame_locator('iframe[title="合同修订文档"]').locator('article')).to_contain_text('验收后15日付款。')
        page.screenshot(path='artifacts/functional-workbench.png')
        page.get_by_text('审查设置',exact=True).click()
        page.get_by_role('button',name='修改审查条件',exact=True).click()
        expect(page.get_by_role('button',name='添加资料',exact=True)).to_be_visible()
        page.get_by_role('button',name='添加要求',exact=True).click()
        fields = page.get_by_placeholder('每条填写一项可核验的要求')
        fields.last.fill('设备应附带验收材料')
        page.get_by_role('button',name='保存审查条件',exact=True).click()
        expect(page.get_by_text('审查条件已改变，当前展示上次审查的文档与意见。请重新审查后再处理修订。',exact=True)).to_be_visible()
        assert not errors, errors
        browser.close()


def test_browser_refresh_can_reconnect_background_review(isolated_workspace, monkeypatch):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    monkeypatch.setattr(graph,'get_llm_client',lambda config:None)
    original = workspace_api.review_events
    async def slow(snapshot,config):
        await asyncio.sleep(2)
        async for item in original(snapshot,config):
            yield item
    monkeypatch.setattr(workspace_api,'review_events',slow)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1920,'height':1080})
        errors = []; page.on('pageerror',lambda err:errors.append(str(err)))
        task = page.request.post(base+'/api/tasks',data={'title':'断线重连验收','text':TEXT,'mode':'quick'}).json()
        page.goto(base+'/workbench?task='+task['id'])
        page.get_by_role('button',name='开始审查',exact=True).click()
        expect(page.get_by_role('button',name='取消审查',exact=True)).to_be_visible()
        page.reload()
        page.locator('.wb-functional-overview > summary').click()
        page.get_by_role('button',name='重新连接审查进度',exact=True).click()
        page.get_by_role('button',name='查看审查修订稿',exact=True).click()
        expect(page.get_by_role('button',name='重新审查',exact=True)).to_be_enabled()
        saved = page.request.get(base+'/api/tasks/'+task['id']).json()
        assert len(saved['runs']) == 1 and saved['run']['status'] == 'completed'
        assert not errors, errors
        browser.close()


def test_completion_is_atomic_when_run_changes(client, monkeypatch):
    task, run = seed(client)
    original = workspace_api.repo.complete_review
    def concurrent(task_id, task_revision, run_id, run_revision, confirmations):
        workspace_api.repo.update(run_id, {'comments': {'changed':'另一页面修改'}})
        return original(task_id, task_revision, run_id, run_revision, confirmations)
    monkeypatch.setattr(workspace_api.repo,'complete_review',concurrent)
    response = complete(client,task['id'])
    assert response.status_code == 409
    assert workspace_api.repo.get(task['id'])['status'] == 'pending_review'
    assert not workspace_api.repo.get(run['id']).get('confirmed_at')


def test_immediate_cancel_marks_run_interrupted(isolated_workspace):
    async def scenario():
        repo = workspace_api.repo
        task = repo.create('task',{'title':'立即取消','text':TEXT,'status':'draft'})
        run = repo.start_run(task['id'])
        async def events(snapshot, config):
            await asyncio.sleep(100)
            yield 'complete', {}
        job = review_jobs.launch(repo,run,{},events)
        await review_jobs.cancel(repo,run['id'])
        assert job.done and repo.get(run['id'])['status'] == 'interrupted'
        assert repo.get(task['id'])['status'] == 'interrupted'
        await review_jobs.shutdown(repo)
    asyncio.run(scenario())

