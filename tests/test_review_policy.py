import asyncio
import json
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

from backend import graph, workspace_api, workspace_review
from backend.main import app
from backend.review_policy import admit, AdmissionError, verify_requirements, evidence_loop, requirements_for


TEXT = '第一条 设备交付。\n第二条 验收后30日付款。'
REQ = {'id': 'r1', 'text': '付款期限不超过30日', 'priority': 'required', 'source': '用户要求'}


def test_defaults_and_policy_confirmation_validation():
    with TestClient(app) as client:
        base = {'title': '采购', 'text': TEXT, 'mode': 'quick'}
        assert client.post('/api/tasks', json=base).json()['role'] == '中立审慎'
        policy = {'name': '制度.txt', 'text': '付款期限不超过30日', 'kind': 'policy'}
        body = {**base, 'mode': 'deep', 'references': [policy]}
        assert client.post('/api/tasks', json=body).status_code == 422
        policy['confirmed'] = True
        assert client.post('/api/tasks', json=body).status_code == 422
        body['requirements'] = [{**REQ, 'source': policy['name'], 'evidence': policy['text']}]
        assert client.post('/api/tasks', json=body).status_code == 200
        assert client.post('/api/tasks', json={**body, 'mode': 'quick'}).status_code == 200
        policy['text'] = '新制度'
        assert client.post('/api/tasks', json=body).status_code == 422


def test_admission_does_not_use_political_or_illegal_keywords_as_automatic_rejection(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    result = asyncio.run(admit({'text': TEXT + '\n禁止行贿犯罪，政治变化依约处理。'}, {}, None))
    assert result['status'] == 'pass' and result['safety_status'] == 'needs_review'
    with pytest.raises(AdmissionError):
        asyncio.run(admit({'text': '今天晴天适合散步。'}, {}, None))


@pytest.mark.parametrize('reply', [{'status': 'rejected', 'reason': '请求协助实施犯罪'}, {}, {'status': 'unknown'}])
def test_admission_model_rejection_or_invalid_reply_stops_review(monkeypatch, reply):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    async def model(config, prompt):
        return reply
    monkeypatch.setattr(workspace_review, 'model_json', model)
    with TestClient(app) as client:
        task = client.post('/api/tasks', json={'title': '准入', 'text': TEXT, 'mode': 'quick'}).json()
        response = client.post('/api/tasks/' + task['id'] + '/review/stream', json={})
        assert 'event: error' in response.text and 'event: complete' not in response.text
        run = workspace_api.repo.list('run', task['id'])[0]
        assert run['admission']['status'] in ('rejected', 'needs_review')
        assert run['status'] == 'failed' and run['result'] is None
        assert not any(item['stage'] == 'segment_contract' for item in run['audit_trace'])


@pytest.mark.parametrize('evidence,conflicts', [('虚构条款', []), ('', []), ('验收后30日付款。', ['r2'])])
def test_false_evidence_and_conflicts_cannot_pass(monkeypatch, evidence, conflicts):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    async def model(config, prompt):
        return {'findings': [{'id': 'r1', 'status': 'pass', 'evidence': evidence, 'explanation': '满足', 'conflict_with': conflicts}]}
    result = asyncio.run(verify_requirements({'text': TEXT}, [REQ], {}, model))
    assert result[0]['status'] == 'needs_review'


def test_missing_requirement_id_keeps_entire_batch_pending(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    async def model(config, prompt):
        return {'findings': []}
    result = asyncio.run(verify_requirements({'text': TEXT}, [REQ], {}, model))
    assert len(result) == 1 and result[0]['status'] == 'needs_review'


def test_requirement_snapshot_report_and_csv(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with TestClient(app) as client:
        task = client.post('/api/tasks', json={'title': '=1+1', 'text': TEXT, 'mode': 'quick', 'requirements': [REQ]}).json()
        response = client.post('/api/tasks/' + task['id'] + '/review/stream', json={})
        assert 'event: complete' in response.text
        run = workspace_api.repo.list('run', task['id'])[0]
        assert run['input']['requirements'][0]['text'] == REQ['text']
        assert run['result']['requirement_findings'][0]['status'] == 'needs_review'
        assert len(run['result']['input_digest']) == 64
        report = client.get('/api/runs/' + run['id'] + '/export?scope=report')
        document = Document(BytesIO(report.content))
        assert REQ['text'] in '\n'.join(p.text for p in document.paragraphs)
        stats = client.get('/api/reports/reviews').json()
        assert stats['statuses']['completed'] == 1
        assert "'=1+1" in client.get('/api/reports/reviews?format=csv').content.decode('utf-8-sig')


def test_react_uses_observed_tool_and_stops_at_limit(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    calls = []
    async def model(config, prompt):
        calls.append(prompt)
        return {'action': 'search', 'query': '付款'}
    findings = [{**REQ, 'status': 'needs_review', 'conflict_with': []}]
    result = asyncio.run(evidence_loop({'text': TEXT}, findings, {}, model))
    assert result['status'] == 'incomplete' and len(calls) == 3
    assert '验收后30日付款' in calls[1]
    assert findings[0]['status'] == 'needs_review'


def test_extraction_requires_real_source_quote(monkeypatch):
    async def model(config, prompt):
        return {'requirements': [{'text': '不得超过30日', 'priority': 'required', 'evidence': '不存在的原文'}]}
    monkeypatch.setattr(workspace_api, 'model_json', model)
    with TestClient(app) as client:
        response = client.post('/api/requirements/extract', json={'material': {'name': '制度.txt', 'text': '付款期限不超过30日'}})
        assert response.status_code == 422


def test_policy_upload_confirmation_and_snapshot_in_browser(monkeypatch):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base)
        page.get_by_role('button', name='✍️ 粘贴正文', exact=True).click()
        page.get_by_label('合同正文', exact=True).fill(TEXT)
        page.get_by_placeholder('填写便于识别的合同名称').fill('公司制度浏览器核验')
        page.get_by_text('补充交易背景与参考资料', exact=True).click()
        page.locator('details input[type=file][accept=".docx,.pdf,.txt"]').set_input_files({'name': '制度.txt', 'mimeType': 'text/plain', 'buffer': '付款期限不超过30日'.encode()})
        page.get_by_label('资料用途').select_option('policy')
        page.get_by_role('button', name='手动录入要求', exact=True).click()
        page.get_by_placeholder('每条填写一项可核验的要求').fill(REQ['text'])
        page.get_by_label('我已核对下方要求，确认完整准确').check()
        page.get_by_role('button', name='进入工作台核对合同', exact=True).click()
        page.wait_for_url('**/workbench?task=*')
        task_id = page.url.split('task=')[1]
        saved = workspace_api.repo.get(task_id)
        assert saved['role'] == '中立审慎'
        assert saved['references'][0]['confirmed']
        assert saved['requirements'][0]['text'] == REQ['text']
        assert not errors
        browser.close()


def test_all_priority_sources_are_retained_and_namespaced():
    snapshot = {'focus':'优先核对付款期限','requirements':[{**REQ,'source':'公司制度.txt'}],
                'background':'分批验收、分期付款','references':[{'name':'公司制度.txt','kind':'policy','confirmed':True}],
                'checklist':{'name':'发票清单','items':[{'id':'r1','requirement':'应约定开具专用发票'}]}}
    requirements = requirements_for(snapshot)
    assert len(requirements) == 3
    assert {item['origin'] for item in requirements} == {'reference','custom','checklist'}
    assert len({item['id'] for item in requirements}) == 3
    assert any(item['text'] == '应约定开具专用发票' for item in requirements)


def test_background_references_and_all_requirements_reach_every_verification_batch(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    snapshot = {'text':TEXT,'focus':'优先核对付款期限','background':'分批验收、分期付款',
                'references':[{'name':'交易说明.txt','text':'付款须经确认','kind':'reference'}],
                'checklist':{'name':'专项清单','items':[{'id':'vat','requirement':'应明确发票类型'}]}}
    requirements = requirements_for(snapshot)
    prompts=[]
    async def model(config,prompt):
        prompts.append(prompt)
        return {'findings':[{'id':item['id'],'status':'needs_review','evidence':'','explanation':'须人工核对','conflict_with':[]} for item in requirements]}
    findings = asyncio.run(verify_requirements(snapshot, requirements, {}, model))
    assert len(findings) == 2
    assert all(text in prompts[0] for text in ['分批验收、分期付款','交易说明.txt','付款须经确认','优先核对付款期限','应明确发票类型'])
