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


def test_one_click_undo_resets_accepted_and_rejected_decisions(revision_client):
    from backend import workspace_api
    task,run=seed_review(revision_client,True)
    with live_server() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1920,'height':1000})
        page.goto(base+'/workbench?task='+task['id'])
        preview=page.frame_locator('iframe[title="合同修订文档"]')
        expect(preview.locator('article ins')).not_to_have_count(0)
        undo=page.get_by_role('button',name='一键撤销',exact=True)
        expect(undo).to_be_disabled()
        page.locator('#card-payment').get_by_role('button',name='采纳',exact=True).click()
        expect(page.locator('#card-payment')).to_have_attribute('data-decision','applied')
        page.locator('#card-liability').get_by_role('button',name='拒绝',exact=True).click()
        expect(page.locator('#card-liability')).to_have_attribute('data-decision','rejected')
        expect(undo).to_be_enabled()
        page.get_by_label('筛选处理状态').select_option('applied')
        undo.click()
        expect(undo).to_be_disabled()
        saved=workspace_api.repo.get(run['id'],'run')
        assert saved['applied']==[] and saved['decisions']=={'payment':'pending','liability':'pending'}
        page.get_by_label('筛选处理状态').select_option('all')
        expect(preview.locator('[data-review-issue="payment"] ins')).not_to_have_count(0)
        expect(preview.locator('[data-review-issue="liability"] ins')).not_to_have_count(0)
        buttons=page.locator('.wb-batch-actions button')
        assert all(buttons.nth(i).bounding_box()['height']>=42 for i in range(2))
        assert abs(page.locator('.wb-document-toolbar').bounding_box()['width']-960)<2
        assert abs(page.locator('#review-summary-panel').bounding_box()['width']-384)<2
        assert abs(page.locator('#opinion-drawer').bounding_box()['width']-576)<2
        page.screenshot(path='artifacts/prototypes/batch-actions-wide-document.png')
        browser.close()


def test_253_columns_tight_paper_and_collapsible_navigation(revision_client):
    task,run=seed_review(revision_client,True)
    with live_server() as base,sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1920,'height':1000})
        page.goto(base+'/workbench?task='+task['id'])
        preview=page.frame_locator('iframe[title="合同修订文档"]')
        expect(preview.locator('section.docx')).not_to_have_count(0)
        for width in [1920,1440,1280]:
            page.set_viewport_size({'width':width,'height':1000})
            page.wait_for_function('(width)=>Math.abs(document.querySelector(".wb-document-toolbar").getBoundingClientRect().width-width*.5)<2',arg=width)
            for selector,ratio in [('#review-summary-panel',.2),('.wb-document-toolbar',.5),('#opinion-drawer',.3)]:
                assert abs(page.locator(selector).bounding_box()['width']-width*ratio)<2
            preview.locator('body').evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            geometry=preview.locator('#viewport').evaluate('(el)=>({width:el.clientWidth,scrollWidth:el.scrollWidth,left:document.querySelector("section.docx").getBoundingClientRect().left,right:document.querySelector("section.docx").getBoundingClientRect().right})')
            assert geometry['left']<16 and geometry['width']-geometry['right']<16,geometry
            assert geometry['scrollWidth']<=geometry['width']+1,geometry
        before=page.locator('.wb-document-toolbar').bounding_box()['width']
        right=page.locator('#opinion-drawer').bounding_box()['width']
        page.get_by_role('button',name='收起审查导航',exact=True).click()
        expect(page.get_by_role('button',name='展开审查导航',exact=True)).to_be_visible()
        assert page.locator('#review-summary-panel').bounding_box()['width']==36
        assert page.locator('.wb-document-toolbar').bounding_box()['width']>before+100
        assert page.locator('#opinion-drawer').bounding_box()['width']>right+70
        assert page.locator('#opinion-drawer .wb-risk-description').first.evaluate('(el)=>getComputedStyle(el).fontSize')=='15px'
        assert page.locator('#opinion-drawer .revision-clause-preview ins').first.evaluate('(el)=>getComputedStyle(el).fontSize')=='15px'
        assert page.locator('#opinion-drawer .prototype-card-title').first.evaluate('(el)=>getComputedStyle(el).fontSize')=='16px'
        page.get_by_role('button',name='展开审查导航',exact=True).click()
        assert abs(page.locator('#review-summary-panel').bounding_box()['width']-1280*.2)<2
        browser.close()
