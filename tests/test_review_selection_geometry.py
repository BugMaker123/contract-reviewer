from test_tracked_revisions import revision_client, seed_review
from test_ui_composition import live_server
from playwright.sync_api import sync_playwright, expect


def test_issue_navigation_and_advice_share_one_accordion(revision_client):
    task, _ = seed_review(revision_client)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={'width': 1600, 'height': 1000})
            page.goto(base + '/workbench?task=' + task['id'])
            expect(page.locator('#review-summary-panel .wb-nav-issues')).to_have_count(0)
            payment = page.locator('#card-payment .wb-issue-accordion-trigger')
            liability = page.locator('#card-liability .wb-issue-accordion-trigger')
            expect(payment).to_have_attribute('aria-expanded', 'true')
            expect(liability).to_have_attribute('aria-expanded', 'false')
            liability.click()
            expect(payment).to_have_attribute('aria-expanded', 'false')
            expect(liability).to_have_attribute('aria-expanded', 'true')
            expect(page.locator('#card-liability .prototype-locate')).to_be_visible()
            liability.click()
            expect(liability).to_have_attribute('aria-expanded', 'false')
        finally:
            browser.close()


def test_continuous_clause_has_one_box_inside_viewport(revision_client):
    from backend import workspace_api
    task, run = seed_review(revision_client)
    original = '年度采购协议\n甲方：示例公司\n地址：示例地址\n乙方：采购公司'
    issue = run['result']['issues'][0]
    issue['redline'].update(original_text=original, suggested_text=original + '\n双方应核实主体信息。')
    workspace_api.repo.update(task['id'], {'text': original})
    workspace_api.repo.update(run['id'], {'input': {**run['input'], 'text': original}, 'result': {**run['result'], 'issues': [issue]}})
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1000})
        page.goto(base + '/workbench?task=' + task['id'])
        preview = page.frame_locator('iframe[title="合同修订文档"]')
        expect(preview.locator('article ins')).to_be_visible()
        page.locator('#card-payment .prototype-locate').click()
        expect(preview.locator('#review-selection')).to_be_visible()
        for width in [1920, 1280]:
            page.set_viewport_size({'width': width, 'height': 1000})
            preview.locator('body').evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            page.screenshot(path='artifacts/review-selection-fixed.png', full_page=True)
            assert preview.locator('body').evaluate('''() => {
                const viewport = document.querySelector('#viewport');
                const v = viewport.getBoundingClientRect();
                const paragraphs = [...document.querySelectorAll('article p.review-clause')].map(el => el.getBoundingClientRect());
                const boxes = [...document.querySelectorAll('.review-selection-box')].filter(el => !el.hidden).map(el => el.getBoundingClientRect());
                return boxes.length === 1 && boxes.every(r =>
                    r.left >= v.left && r.right <= v.left + viewport.clientWidth + 1 &&
                    r.top >= v.top && r.bottom <= v.top + viewport.clientHeight + 1 &&
                    r.top <= paragraphs[0].bottom && r.bottom >= paragraphs.at(-1).top);
            }''')
        page.set_viewport_size({'width': 1920, 'height': 1000})
        page.screenshot(path='artifacts/review-selection-fixed.png', full_page=True)
        browser.close()
