import pytest

from backend import workspace_api
from test_functional_completeness import client, seed, REQ


@pytest.mark.parametrize('status', ['pass', 'needs_review', 'fail'])
def test_finish_keeps_requirement_findings_display_only(client, monkeypatch, status):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect

    calls = []
    async def verify(snapshot, requirements, config, model_json, *, text=None):
        calls.append(text)
        return [{**item, 'status': status, 'evidence': text if status == 'pass' else '',
                 'explanation': '测试当前稿核验', 'conflict_with': []} for item in requirements]
    monkeypatch.setattr(workspace_api, 'verify_requirements', verify)
    task, run = seed(client, [REQ])
    result = {**run['result'], 'issues':[{'id':'optional', 'severity':'warning', 'clause_title':'一般风险', 'issue_title':'可选完善', 'risk_analysis':'一般建议', 'redline':None}], 'requirement_findings':[{**REQ, 'status':status, 'explanation':'重点要求核验结论', 'evidence':'', 'conflict_with':[]}]}
    run = workspace_api.repo.update(run['id'], {'result':result})
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/workbench?task=' + task['id'])
        page.get_by_role('button', name='完成审核', exact=True).click()
        expect(page.get_by_role('button', name='已完成审核', exact=True)).to_be_visible()
        assert calls == []
        expect(page.get_by_text('完成审核前确认',exact=True)).to_have_count(0)
        expect(page.get_by_placeholder('说明处理方式、确认依据或接受风险的理由')).to_have_count(0)
        assert workspace_api.repo.get(run['id'])['result']['requirement_findings']==result['requirement_findings']
        assert not errors
        browser.close()


@pytest.mark.parametrize('severity,decision,blocked', [
    ('critical', 'pending', True), ('critical', 'needs_review', True),
    ('critical', 'rejected', False), ('critical', 'applied', False),
    ('warning', 'pending', False), ('warning', 'needs_review', False),
    ('info', 'pending', False), ('favorable', 'pending', False),
])
def test_finish_only_requires_serious_risks_handled(client, severity, decision, blocked):
    task, run = seed(client)
    issue = {'id':'policy-test', 'severity':severity, 'issue_title':'test'}
    workspace_api.repo.update(run['id'], {
        'result':{**run['result'], 'issues':[issue]}, 'decisions':{'policy-test':decision},
    })
    response = client.post('/api/tasks/'+task['id']+'/complete', json={'revision':task['revision'], 'archived':False})
    assert response.status_code == (409 if blocked else 200), response.text
    saved = workspace_api.repo.get(run['id'])
    assert saved['decisions']['policy-test'] == decision


def test_rereview_model_receives_accepted_history(monkeypatch):
    from backend import graph
    messages = []
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    def invoke(client, prompt, config):
        messages.extend(prompt)
        return {'tax_settlement':{}, 'issues':[]}
    monkeypatch.setattr(graph, 'invoke_review_with_retry', invoke)
    graph.node_balance_review({
        'review_mode':'deep', 'contract_text':'current accepted document', 'party_role':'neutral',
        'segments':[], 'prior_resolutions':[{'issue_title':'previous risk', 'accepted_text':'accepted safeguard'}],
    })
    assert 'accepted safeguard' in messages[-1].content
    assert 'previous risk' in messages[-1].content
