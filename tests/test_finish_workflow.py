import pytest

from backend import workspace_api
from test_functional_completeness import client, seed, REQ


@pytest.mark.parametrize('status', ['pass', 'needs_review'])
def test_finish_automatically_verifies_and_exposes_required_confirmation(client, monkeypatch, status):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect

    calls = []
    async def verify(snapshot, requirements, config, model_json, *, text=None):
        calls.append(text)
        return [{**item, 'status': status, 'evidence': text if status == 'pass' else '',
                 'explanation': '测试当前稿核验', 'conflict_with': []} for item in requirements]
    monkeypatch.setattr(workspace_api, 'verify_requirements', verify)
    task, run = seed(client, [REQ])
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/workbench?task=' + task['id'])
        page.get_by_role('button', name='完成审核', exact=True).click()
        if status == 'needs_review':
            reason = page.get_by_placeholder('说明处理方式、确认依据或接受风险的理由')
            expect(reason).to_be_visible()
            expect(reason).to_be_focused()
            assert workspace_api.repo.get(task['id'])['status'] == 'pending_review'
            reason.fill('已经人工核对并确认当前付款条款满足要求')
            page.get_by_role('button', name='完成审核', exact=True).click()
        expect(page.get_by_role('button', name='已完成审核', exact=True)).to_be_visible()
        assert len(calls) == 1
        assert calls[0] == run['input']['text']
        assert not errors
        browser.close()
