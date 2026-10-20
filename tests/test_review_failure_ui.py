from copy import deepcopy
import pytest
from backend import workspace_api
from backend.review_policy import AdmissionError
from test_tracked_revisions import revision_client, seed_review


@pytest.mark.parametrize('previous_result', [False, True])
def test_admission_failure_shows_reason_without_success_labels(revision_client, monkeypatch, previous_result):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    if previous_result:
        task, previous = seed_review(revision_client)
    else:
        task = revision_client.post('/api/tasks', json={'title': '审查停止提示', 'text': '第一条 验收后付款。', 'mode': 'quick'}).json()
    reason = '当前材料是合同审查意见书，请上传合同原文后重试。'
    async def rejected(snapshot, config):
        decision = {'status': 'needs_review', 'reason': reason}
        yield 'progress', {'stage': 'admission', 'detail': reason, 'admission': decision}
        raise AdmissionError(decision)
    monkeypatch.setattr(workspace_api, 'review_events', rejected)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base + '/workbench?task=' + task['id'])
        if previous_result:
            page.locator('.prototype-navbar').get_by_role('button', name='重新审查', exact=True).click()
            dialog = page.get_by_role('dialog', name='选择重新审查稿件')
            dialog.locator('input[value="task"]').check()
            dialog.get_by_role('button', name='确认并开始审查', exact=True).click()
        else:
            page.get_by_role('button', name='开始审查', exact=True).click()
        dialog = page.get_by_role('dialog', name='合同合规性审查分析')
        expect(dialog.get_by_role('alert')).to_contain_text(reason)
        expect(dialog.get_by_text('未通过审查准入', exact=True)).to_be_visible()
        expect(dialog.get_by_text('已完成校验', exact=True)).to_have_count(0)
        expect(dialog.get_by_text('本次未识别出审查问题', exact=True)).to_have_count(0)
        expect(dialog.get_by_role('button', name='查看审查修订稿', exact=True)).to_have_count(0)
        expect(dialog.get_by_role('button', name='返回工作台', exact=True)).to_be_visible()
        expect(dialog.locator('.review-stage-list li.active')).to_have_count(0)
        assert '后台任务仍在运行' not in dialog.inner_text()
        current = page.request.get(base + '/api/tasks/' + task['id']).json()
        assert current['status'] == 'failed'
        if previous_result:
            assert current['active_run'] == previous['id']
            assert current['run']['result'] == previous['result']
        else:
            assert current['active_run'] is None
        browser.close()
