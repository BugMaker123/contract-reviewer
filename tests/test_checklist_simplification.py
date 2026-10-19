"""Minimal authoring, safe bulk imports and optional rule configuration."""
from playwright.sync_api import sync_playwright, expect
from test_ui_composition import live_server


def test_minimal_checklist_bulk_import_and_default_selection(isolated_workspace):
    with live_server() as base,sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto(base+'/checklists')
        page.get_by_role('button',name='＋ 创建审查清单',exact=True).click()
        dialog=page.get_by_role('dialog',name='创建审查清单')
        expect(dialog.get_by_label('检查项标题',exact=True)).not_to_be_visible()
        dialog.get_by_placeholder('如：采购合同审查要求').fill('简洁采购要求')
        dialog.get_by_label('检查项要求',exact=True).fill('付款前必须完成验收')
        dialog.get_by_role('button',name='批量粘贴',exact=True).click()
        dialog.locator('#checklist-batch-input').fill('1. 付款前必须完成验收\n2. 违约责任应约定赔偿上限\n3. 明确交付时间')
        dialog.get_by_role('button',name='添加这些要求',exact=True).click()
        expect(dialog.get_by_label('检查项要求',exact=True)).to_have_count(3)
        dialog.locator('input[type=file]').set_input_files({'name':'补充要求.txt','mimeType':'text/plain','buffer':'明确交付时间\n约定争议解决方式\n1.1 资料清单须完整'.encode()})
        expect(dialog.get_by_label('检查项要求',exact=True)).to_have_count(5)
        expect(dialog.get_by_label('检查项要求',exact=True).first).to_have_value('付款前必须完成验收')
        page.screenshot(path='artifacts/checklist-editor-simple.png')
        dialog.get_by_role('button',name='保存并启用',exact=True).click()
        row=page.get_by_role('row').filter(has=page.get_by_text('简洁采购要求',exact=True))
        expect(row).to_be_visible()
        lists=page.request.get(base+'/api/checklists').json()['items'];saved=lists[0]
        assert saved['published'] and len(saved['items'])==5
        assert all(item['operator']=='semantic' and item['severity']=='warning' for item in saved['items'])
        assert saved['items'][0]['title']=='付款前必须完成验收'
        assert saved['items'][-1]['requirement']=='1.1 资料清单须完整'
        page.screenshot(path='artifacts/checklists-simple-list.png')
        row.get_by_role('link',name='使用清单 →',exact=True).click()
        expect(page.get_by_text('已勾选 5 项',exact=True)).to_be_visible()
        expect(page.locator('.checklist-selection')).not_to_have_attribute('open','')
        expect(page.locator('.checklist-option').first).not_to_be_visible()
        page.get_by_role('button',name='✍️ 粘贴正文',exact=True).click()
        page.get_by_role('textbox',name='合同正文',exact=True).fill('第一条 标的为设备。第二条 验收后付款。')
        page.get_by_placeholder('填写便于识别的合同名称').fill('默认全项审查验收')
        page.get_by_role('button',name='进入工作台核对合同',exact=True).click()
        page.wait_for_url('**/workbench?task=*')
        item=page.request.get(base+'/api/tasks/'+page.url.split('task=')[1]).json()
        assert len(item['checklist']['items'])==5
        assert not errors,errors
        browser.close()


def test_advanced_rules_survive_simple_edit_and_failed_bulk_import(isolated_workspace):
    with live_server() as base,sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':900})
        saved=page.request.post(base+'/api/checklists',data={'name':'已有文字规则','published':True,'items':[{'id':'invoice','title':'发票要求','requirement':'必须提供增值税专用发票','operator':'contains_all','keywords':['增值税','专用发票'],'severity':'critical','suggestion':'明确发票类型'}]}).json()
        task=page.request.post(base+'/api/tasks',data={'title':'历史清单任务','text':'第一条 付款。第二条 发票。','mode':'checklist','checklist_id':saved['id']}).json()
        page.goto(base+'/checklists')
        page.get_by_role('button',name='编辑清单',exact=True).click()
        dialog=page.get_by_role('dialog',name='编辑审查清单')
        expect(dialog.get_by_label('检查项标题',exact=True)).not_to_be_visible()
        dialog.locator('input[type=file]').set_input_files({'name':'过长清单.txt','mimeType':'text/plain','buffer':'\n'.join('新增要求'+str(i) for i in range(101)).encode()})
        expect(dialog.get_by_role('alert')).to_contain_text('最多100条')
        expect(dialog.get_by_label('检查项要求',exact=True)).to_have_count(1)
        dialog.get_by_label('检查项要求',exact=True).fill('交易文件须约定增值税专用发票')
        dialog.get_by_role('button',name='保存并启用',exact=True).click()
        expect(page.get_by_role('dialog',name='编辑审查清单')).to_have_count(0)
        updated=page.request.get(base+'/api/checklists/'+saved['id']).json()
        item=updated['items'][0]
        assert item['title']=='发票要求' and item['operator']=='contains_all'
        assert item['keywords']==['增值税','专用发票'] and item['severity']=='critical' and item['suggestion']=='明确发票类型'
        assert updated['version']==saved['version']+1
        old=page.request.get(base+'/api/tasks/'+task['id']).json()['checklist']
        assert old['items'][0]['requirement']=='必须提供增值税专用发票'
        assert old['version']==saved['version']
        browser.close()
