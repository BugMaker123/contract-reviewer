from test_tracked_revisions import revision_client,seed_review
from test_ui_composition import live_server
from playwright.sync_api import sync_playwright,expect


def test_support_actions_are_grouped_without_duplicate_rejection(revision_client):
    task,run=seed_review(revision_client,True)
    with live_server() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1600,'height':1000})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/workbench?task='+task['id'])
        card=page.locator('#card-payment')
        expect(card.get_by_role('button',name='采纳',exact=True)).to_be_visible()
        expect(card.get_by_role('button',name='拒绝',exact=True)).to_have_count(1)
        expect(card.get_by_role('button',name='不采纳',exact=True)).to_have_count(0)
        expect(card.get_by_role('button',name='重新生成',exact=True)).to_have_count(0)
        expect(card.get_by_role('button',name='撤销操作',exact=True)).to_be_disabled()
        card.locator('.revision-support-tools > summary').click()
        expect(card.get_by_role('button',name='手动调整修订',exact=True)).to_be_visible()
        expect(card.get_by_role('button',name='编辑正文',exact=True)).to_be_visible()
        card.locator('.compact-extra-tools > summary').click()
        expect(card.get_by_label('条目处理备注')).to_be_visible()
        card.get_by_role('button',name='标记待复核',exact=True).click()
        expect(card).to_have_attribute('data-decision','needs_review')
        card.get_by_role('button',name='撤销操作',exact=True).click()
        expect(card).to_have_attribute('data-decision','pending')
        assert card.locator('.compact-extra-tools').bounding_box()['width'] >= card.bounding_box()['width'] - 40
        expect(card.get_by_role('button',name='撤销操作',exact=True)).to_be_disabled()
        card.get_by_role('button',name='采纳',exact=True).click()
        expect(card).to_have_attribute('data-decision','applied')
        card.get_by_role('button',name='撤销操作',exact=True).click()
        expect(card).to_have_attribute('data-decision','pending')
        card.get_by_role('button',name='拒绝',exact=True).click()
        expect(card).to_have_attribute('data-decision','rejected')
        card.get_by_role('button',name='撤销操作',exact=True).click()
        expect(card).to_have_attribute('data-decision','pending')
        preview=page.frame_locator('iframe[title="合同修订文档"]')
        expect(preview.locator('[data-review-issue="payment"] ins')).not_to_have_count(0)
        assert not errors,errors
        browser.close()
