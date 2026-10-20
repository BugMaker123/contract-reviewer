import pytest
from copy import deepcopy
from backend import workspace_api
from test_tracked_revisions import revision_client, seed_review


@pytest.mark.parametrize('save_failure', [False, True])
def test_cancel_accepted_batch_preserves_other_decisions_and_notes(revision_client, save_failure):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    task, run = seed_review(revision_client, True)
    result = deepcopy(run['result'])
    result['issues'].append({**result['issues'][1], 'id': 'untouched', 'redline': None})
    run = workspace_api.repo.update(run['id'], {'result': result}, run['revision'])
    handled = revision_client.put('/api/runs/' + run['id'] + '/handling', json={
        'revision': run['revision'], 'applied': ['payment', 'liability'],
        'decisions': {'payment': 'applied', 'liability': 'applied', 'untouched': 'rejected'},
        'comments': {'payment': '付款条款已核对', 'liability': '保留原约定'}})
    assert handled.status_code == 200
    current = revision_client.get('/api/tasks/' + task['id']).json()
    assert revision_client.post('/api/tasks/' + task['id'] + '/complete', json={'revision': current['revision'], 'archived': False}).status_code == 200
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/workbench?task=' + task['id'])
        frame = page.frame_locator('iframe[title="合同修订文档"]')
        expect(frame.locator('.review-applied')).not_to_have_count(0)
        cancel = page.get_by_role('button', name='一键取消已采纳', exact=True)
        expect(cancel).to_be_enabled()
        # Batch operates on the entire run even if cards are filtered out.
        page.get_by_role('textbox', name='搜索审查意见', exact=True).fill('不匹配的筛选条件')
        if save_failure:
            page.route('**/api/runs/*/handling', lambda route: route.fulfill(status=409, json={'detail': '版本冲突，请刷新'}))
        writes = []
        page.on('request', lambda request: writes.append(request) if request.method == 'PUT' and request.url.endswith('/handling') else None)
        with page.expect_response(lambda response: response.request.method == 'PUT' and response.url.endswith('/handling')):
            cancel.click()
        if save_failure:
            expect(page.get_by_text('取消采纳失败：版本冲突，请刷新', exact=True)).to_be_visible()
            expect(cancel).to_be_enabled()
            expect(frame.locator('.review-applied')).not_to_have_count(0)
        else:
            expect(cancel).to_be_disabled()
            expect(frame.locator('.review-applied')).to_have_count(0)
            expect(page.get_by_role('button', name='完成审核', exact=True)).to_be_visible()
        saved = page.request.get(base + '/api/tasks/' + task['id']).json()
        assert saved['run']['comments'] == {'payment': '付款条款已核对', 'liability': '保留原约定'}
        assert saved['run']['decisions']['untouched'] == 'rejected'
        assert saved['run']['decisions']['liability'] == ('applied' if save_failure else 'pending')
        assert saved['run']['applied'] == (['payment', 'liability'] if save_failure else [])
        assert saved['run']['decisions']['payment'] == ('applied' if save_failure else 'pending')
        assert saved['status'] == ('completed' if save_failure else 'pending_review')
        assert len(writes) == 1
        if not save_failure:
            assert page.request.get(base + '/api/runs/' + run['id'] + '/export').status == 409
            page.reload()
            expect(cancel).to_be_disabled()
            expect(frame.locator('.review-applied')).to_have_count(0)
        assert not errors, errors
        browser.close()
