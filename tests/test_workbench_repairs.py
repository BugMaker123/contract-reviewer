from test_tracked_revisions import revision_client, seed_review
from test_ui_composition import live_server
from playwright.sync_api import sync_playwright, expect
from backend import workspace_api


def ready_review(client):
    task, run = seed_review(client, True)
    # These interaction tests use fixed proposals and do not require an LLM.
    run = workspace_api.repo.update(run['id'], {'status':'completed'})
    workspace_api.repo.update(task['id'], {'status':'pending_review'})
    return task, run


def test_menu_overview_colors_and_batch_roundtrip(revision_client):
    task, run = ready_review(revision_client)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1920, 'height':1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base + '/workbench?task=' + task['id'])
        expect(page.locator('.workspace-sidebar')).to_be_visible()
        expect(page.locator('#opinion-drawer .wb-integrated-overview')).to_be_visible()
        expect(page.get_by_label('筛选风险等级', exact=True)).to_have_count(0)
        tabs = page.get_by_role('group', name='按风险等级筛选')
        critical = tabs.get_by_role('button', name='重大风险')
        critical.click()
        expect(critical).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('.prototype-risk-card')).to_have_count(0)
        tabs.get_by_role('button', name='一般风险').click()
        expect(page.locator('.prototype-risk-card')).to_have_count(2)
        tabs.get_by_role('button', name='一般风险').click()
        expect(tabs.get_by_role('button', name='全部意见')).to_have_attribute('aria-pressed', 'true')
        preview = page.frame_locator('iframe[title="合同修订文档"]')
        pending = preview.locator('[data-review-issue="payment"] ins').first
        expect(pending).to_be_visible()
        assert pending.evaluate('(el)=>getComputedStyle(el).color') == 'rgb(36, 91, 219)'
        clause = preview.locator('[data-review-issue="payment"]')
        assert clause.evaluate('(el)=>getComputedStyle(el).backgroundColor') == 'rgba(0, 0, 0, 0)'
        assert clause.evaluate('(el)=>getComputedStyle(el).boxShadow') == 'none'
        assert preview.locator('#review-selection').evaluate('(el)=>getComputedStyle(el).backgroundColor') == 'rgba(0, 0, 0, 0)'
        page.screenshot(path='artifacts/prototypes/workbench-word-markup.png')
        accept = page.get_by_role('button', name='一键全部采纳', exact=True)
        expect(accept).to_be_enabled()
        accept.click()
        expect(page.locator('.wb-batch-result').first).to_contain_text('已采纳 2 项')
        expect(preview.locator('[data-review-issue="payment"]')).to_have_class(__import__('re').compile('review-applied'))
        assert preview.locator('[data-review-issue="payment"]').evaluate('(el)=>getComputedStyle(el).color') == 'rgb(22, 115, 67)'
        assert set(workspace_api.repo.get(run['id'], 'run')['applied']) == {'payment', 'liability'}
        page.screenshot(path='artifacts/prototypes/workbench-accepted-green.png')
        page.get_by_role('button', name='一键取消已采纳', exact=True).click()
        expect(accept).to_be_enabled()
        expect(preview.locator('[data-review-issue="payment"] ins').first).to_be_visible()
        assert workspace_api.repo.get(run['id'], 'run')['applied'] == []
        trigger = page.locator('#card-payment .wb-issue-accordion-trigger')
        if trigger.get_attribute('aria-expanded') != 'true':
            trigger.click()
        page.locator('#card-payment').get_by_role('button', name='拒绝', exact=True).click()
        expect(page.locator('#card-payment')).to_have_attribute('data-decision','rejected')
        page.get_by_role('button', name='一键撤销', exact=True).click()
        expect(page.locator('#card-payment')).to_have_attribute('data-decision','pending')
        expect(page.get_by_role('button', name='一键撤销', exact=True)).to_be_disabled()
        page.reload()
        expect(page.locator('#card-payment')).to_have_attribute('data-decision', 'pending')
        expect(preview.locator('[data-review-issue="payment"] ins').first).to_be_visible()
        page.screenshot(path='artifacts/prototypes/workbench-repaired.png')
        assert not errors
        browser.close()


def test_batch_continues_after_conflicting_proposal(revision_client):
    task, run = ready_review(revision_client)
    issues = run['result']['issues']
    issues[0]['redline']['original_text'] = '不存在的原文'
    workspace_api.repo.update(run['id'], {'result':{**run['result'], 'issues':issues}})
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1600,'height':1000})
        page.goto(base + '/workbench?task=' + task['id'])
        page.get_by_role('button', name='一键全部采纳', exact=True).click()
        expect(page.locator('.wb-batch-result').first).to_contain_text('1 项未采纳')
        assert workspace_api.repo.get(run['id'], 'run')['applied'] == ['liability']
        expect(page.locator('.wb-batch-result').first).to_contain_text('冲突')
        browser.close()


def test_execution_overview_opens_from_header(revision_client):
    task, _ = ready_review(revision_client)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1600, 'height':1000})
        page.goto(base + '/workbench?task=' + task['id'])
        button = page.get_by_role('button', name='审查结论与执行记录', exact=True)
        expect(button).to_be_visible()
        report = page.get_by_role('button', name='审查意见书', exact=True)
        assert button.bounding_box()['x'] < report.bounding_box()['x']
        expect(page.locator('#review-summary-panel .wb-functional-overview')).to_have_count(0)
        button.click()
        dialog = page.get_by_role('dialog', name='审查结论与执行记录', exact=True)
        expect(dialog).to_be_visible()
        expect(dialog.get_by_text('审查总评', exact=True)).to_be_visible()
        page.keyboard.press('Escape')
        expect(dialog).to_have_count(0)
        expect(button).to_be_focused()
        button.click()
        dialog.get_by_role('button', name='关闭审查结论与执行记录').click()
        expect(dialog).to_have_count(0)
        browser.close()
