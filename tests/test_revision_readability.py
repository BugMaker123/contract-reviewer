from test_tracked_revisions import revision_client, seed_review
from backend import workspace_api


def test_long_revision_card_and_document_zoom(revision_client):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    task,run=seed_review(revision_client,True)
    run['result']['issues'][0]['redline']['suggested_text']='1. 验收合格后30日付款。\n'+('双方应书面确认交付与验收安排，明确质量异议期限及付款条件。\n'*25)
    workspace_api.repo.update(run['id'],{'result':run['result']})
    with live_server() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1600,'height':1000})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'/workbench?task='+task['id'])
        select=page.get_by_label('合同阅读缩放',exact=True)
        expect(select).to_have_value('1.15')
        frame=page.frame_locator('iframe[title="合同修订文档"]')
        expect(frame.locator('#pages section.docx').first).to_be_visible()
        expect(frame.locator('#pages')).to_have_css('zoom','1.15')
        select.select_option('1.25')
        expect(frame.locator('#pages')).to_have_css('zoom','1.25')
        select.select_option('fit')
        expect(frame.locator('#zoom-percent')).to_have_text('适应宽度')
        card=page.locator('.prototype-risk-card').first
        if not card.locator('.revision-clause-preview').is_visible():
            card.locator('.prototype-risk-card-header').click()
        original=card.locator('.revision-diff-original del')
        expect(original).to_be_visible()
        assert original.evaluate('(el)=>parseFloat(getComputedStyle(el).fontSize)')>=15
        preview=card.locator('.revision-clause-preview')
        assert preview.evaluate('(el)=>el.scrollHeight<=el.clientHeight+2')
        assert preview.bounding_box()['height']>190
        suggested=card.locator('.revision-diff-suggested ins')
        assert suggested.evaluate('(el)=>getComputedStyle(el,"::before").content') in ('none','normal')
        assert not errors,errors
        browser.close()
