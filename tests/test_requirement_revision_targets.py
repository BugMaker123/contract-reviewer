from copy import deepcopy
import pytest
from backend import workspace_api, workspace_review
from backend.review_policy import requirements_for
from backend.revisions import revised_text
from test_tracked_revisions import revision_client, seed_review


def unlocated(client):
    task, run = seed_review(client)
    result = deepcopy(run['result'])
    issue = result['issues'][0]
    issue.update(redline=None, evidence='', segment_id=None, clause_title='自定义要求', requirement_id='focus-1')
    run = workspace_api.repo.update(run['id'], {'result':result})
    return task, run


def test_focus_topics_are_separate_without_splitting_free_form():
    assert [i['text'] for i in requirements_for({'focus':'付款与验收；违约责任；知识产权'})] == ['付款与验收','违约责任','知识产权']
    assert len(requirements_for({'focus':'如果提前付款；应保留验收权'})) == 1
    assert len(requirements_for({'focus':'付款与验收\n知识产权'})) == 2


@pytest.mark.parametrize('kind', ['replace','insert'])
def test_unlocated_requirement_can_be_manually_repaired(revision_client, kind):
    client = revision_client
    _, run = unlocated(client)
    original = '1. 验收后付款。' if kind == 'replace' else ''
    suggested = '1. 验收合格后15日付款。' if kind == 'replace' else '3. 双方对保密信息承担保密义务。'
    response = client.put('/api/runs/'+run['id']+'/issues/payment/revision', json={
        'revision':run['revision'], 'change_type':kind, 'original_text':original, 'suggested_text':suggested})
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved['applied'] == []
    assert saved['result']['issues'][0]['redline']['change_type'] == kind
    assert saved['revision_history']['payment'][-1]['source'] == 'manual'
    text = revised_text(saved, ['payment'])
    assert suggested in text
    if kind == 'replace': assert original not in text
    else: assert text.startswith(run['input']['text'])
    assert client.put('/api/runs/'+run['id']+'/issues/payment/revision', json={
        'revision':run['revision'], 'suggested_text':suggested, 'change_type':kind, 'original_text':original}).status_code == 409


def test_unlocated_target_must_match_real_contract(revision_client):
    client = revision_client
    _, run = unlocated(client)
    url = '/api/runs/'+run['id']+'/issues/payment/revision'
    assert client.put(url,json={'revision':run['revision'],'suggested_text':'修改建议'}).status_code == 409
    assert client.put(url,json={'revision':run['revision'],'original_text':'虚构原文','change_type':'replace','suggested_text':'修改建议'}).status_code == 422
    assert client.put(url,json={'revision':run['revision'],'original_text':'有原文','change_type':'insert','suggested_text':'新增建议'}).status_code == 422
    assert workspace_api.repo.get(run['id'])['revision'] == run['revision']


def test_ai_regeneration_accepts_explicit_target(revision_client, monkeypatch):
    client = revision_client
    _, run = unlocated(client)
    async def model(config, prompt):
        assert '1. 验收后付款。' in prompt
        return {'suggested_text':'1. 验收合格后15日付款。','explanation':'明确付款期限'}
    monkeypatch.setattr(workspace_review, 'model_json', model)
    response = client.post('/api/runs/'+run['id']+'/issues/payment/regenerate',json={
        'revision':run['revision'],'original_text':'1. 验收后付款。','change_type':'replace'})
    assert response.status_code == 200, response.text
    assert response.json()['result']['issues'][0]['redline']['original_text'] == '1. 验收后付款。'


def test_reference_requirement_issues_participate_in_clause_rewrite(monkeypatch):
    import asyncio
    monkeypatch.setattr(workspace_review.graph, 'get_llm_client', lambda config: object())
    original='1. 验收后付款。'
    result={'issues':[{'id':'req-policy-1','segment_id':None,'clause_title':'制度要求','severity':'warning',
        'category':'要求核验','issue_title':'付款期限','legal_basis':'用户重点要求','risk_analysis':'应明确付款期限',
        'negotiation_strategy':'明确期限','redline':None,'evidence':original,'requirement_id':'policy-1'}],
        'segments':[], 'summary':{}}
    async def model(config,prompt):
        assert '付款期限' in prompt
        return {'revisions':[{'id':'req-policy-1','suggested_text':'1. 验收合格后15日付款。'}]}
    monkeypatch.setattr(workspace_review,'model_json',model)
    asyncio.run(workspace_review.consolidate_revisions(result,{'text':original},{}))
    assert result['issues'][0]['redline']['suggested_text']=='1. 验收合格后15日付款。'


def test_browser_unlocated_requirement_has_repair_path(revision_client):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    task, run=unlocated(revision_client)
    with live_server() as address, sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1700,'height':1050})
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto(address+'/workbench?task='+task['id'])
        target=page.locator('.revision-target-editor')
        expect(target).to_be_visible()
        target.get_by_label('待修改的完整原文').fill('1. 验收后付款。')
        card=page.locator('.revision-actions[aria-label="自定义要求修订操作"]')
        card.locator('.revision-more-actions > summary').click()
        card.get_by_role('button',name='手动调整修订',exact=True).click()
        card.get_by_label('自定义要求修订文本',exact=True).fill('1. 验收合格后15日付款。')
        card.get_by_role('button',name='保存修订建议',exact=True).click()
        expect(target).to_have_count(0)
        expect(card.get_by_role('button',name='采纳',exact=True)).to_be_enabled()
        assert workspace_api.repo.get(run['id'])['result']['issues'][0]['redline']['suggested_text']=='1. 验收合格后15日付款。'
        card.get_by_role('button',name='采纳',exact=True).click()
        expect(card.get_by_role('button',name='采纳',exact=True)).to_be_disabled()
        assert 'payment' in workspace_api.repo.get(run['id'])['applied']
        assert not errors
        browser.close()
