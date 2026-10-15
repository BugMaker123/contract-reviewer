"""Browser regression for edits, accepted revisions, and restored previews."""
import socket
import threading

import uvicorn
from playwright.sync_api import sync_playwright, expect
from backend.main import app
from backend import workspace_api, graph
from backend.sample_contracts import SAMPLE_CONTRACTS


def test_preview_follows_edit_and_handling(isolated_workspace, monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            base = f'http://127.0.0.1:{port}'
            page.goto(base)
            text = SAMPLE_CONTRACTS['business_cooperation_contract']['text']
            source = workspace_api.repo.create('source', {'text': text, 'name': 'test.txt', 'extension': '.txt'})
            response = page.request.post(base + '/api/tasks', data={'title': '预览回归', 'type': '采购合同', 'text': text, 'mode': 'quick', 'source_id': source['id']})
            task = response.json()
            page.request.post(base + '/api/tasks/' + task['id'] + '/review/stream', data={})
            page.goto(base + '/workbench?task=' + task['id'])
            expect(page.locator('iframe[title="合同原件预览"]')).to_be_visible()
            page.get_by_role('button', name='采纳此项修订').first.click()
            expect(page.locator('iframe[title="合同原件预览"]')).to_have_count(0)
            expect(page.locator('#contract-viewer')).to_contain_text('仅包含你已采纳的修订（1 项）')
            page.get_by_role('button', name='保存', exact=True).click()
            expect(page.get_by_text('工作内容已保存', exact=True)).to_be_visible()
            page.reload()
            expect(page.locator('#contract-viewer')).to_contain_text('仅包含你已采纳的修订（1 项）')
            page.get_by_role('button', name='撤销采纳').click()
            expect(page.locator('#contract-viewer')).to_contain_text('仅包含你已采纳的修订（0 项）')
            page.get_by_role('button', name='原件预览', exact=True).click()
            page.get_by_role('button', name='编辑条款', exact=True).first.click()
            editor = page.locator('.fixed textarea').last
            original = editor.input_value()
            updated = original + '【浏览器核验修改】'
            editor.fill(updated)
            page.get_by_role('button', name='保存条款', exact=True).click()
            expect(page.locator('#contract-viewer')).to_contain_text(updated)
            expect(page.locator('iframe[title="合同原件预览"]')).to_have_count(0)
            expect(page.locator('#contract-viewer .clause-active')).to_have_count(0)
            page.get_by_role('button', name='保存', exact=True).click()
            expect(page.get_by_text('工作内容已保存', exact=True)).to_be_visible()
            page.reload()
            expect(page.locator('#contract-viewer')).to_contain_text(updated)
            page.get_by_role('button', name='原件预览', exact=True).click()
            page.get_by_role('button', name='编辑正文', exact=True).click()
            body_editor = page.get_by_role('textbox', name='编辑合同正文')
            body_editor.fill(body_editor.input_value() + '\n【整篇正文修改】')
            page.get_by_role('button', name='保存正文', exact=True).click()
            expect(page.locator('#contract-viewer')).to_contain_text('【整篇正文修改】')
            page.get_by_role('button', name='保存', exact=True).click()
            expect(page.get_by_text('工作内容已保存', exact=True)).to_be_visible()
            page.reload()
            expect(page.locator('#contract-viewer')).to_contain_text('【整篇正文修改】')
            page.get_by_role('button', name='重新审查', exact=True).click()
            expect(page.get_by_role('combobox', name='审查历史版本').locator('option')).to_have_count(2, timeout=30000)
            page.reload()
            expect(page.locator('#contract-viewer')).to_contain_text('【整篇正文修改】')
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def test_docx_inline_edit_stays_in_document(isolated_workspace, monkeypatch):
    monkeypatch.setattr(graph, "get_llm_client", lambda config: None)
    from io import BytesIO
    from docx import Document
    document = Document()
    p = document.add_paragraph()
    p.add_run('Payment: ').bold = True
    p.add_run('100 USD').italic = True
    for index in range(35):
        document.add_paragraph(f'Contract paragraph {index}: delivery and payment terms.')
    document.add_paragraph('Special paragraph\nwith a soft break')
    document.add_paragraph('Tabbed\tparagraph')
    document.add_table(rows=1, cols=1).cell(0, 0).text = 'Delivery terms'
    data = BytesIO()
    document.save(data)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            base = f'http://127.0.0.1:{sock.getsockname()[1]}'
            imported = page.request.post(base+'/api/contracts/import', multipart={'file': {'name':'layout.docx','mimeType':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','buffer':data.getvalue()}}).json()
            task = page.request.post(base+'/api/tasks', data={'title':'Inline edit', 'text':imported['text'], 'source_id':imported['source_id']}).json()
            page.request.post(base+'/api/tasks/'+task['id']+'/review/stream', data={})
            record = workspace_api.repo.get(task['id'], 'task')
            run = workspace_api.repo.get(record['active_run'], 'run')
            result = run['result']
            result['issues'][0]['evidence'] = 'Payment: 100 USD'
            result['issues'][0]['redline'] = None
            workspace_api.repo.update(run['id'], {'result': result})
            page.goto(base+'/workbench?task='+task['id'])
            frame = page.frame_locator('iframe[title="合同原件预览"]')
            expect(frame.locator('article p').first).to_contain_text('Payment: 100 USD')
            page.get_by_role('button', name='编辑正文', exact=True).click()
            paragraph = frame.locator('[contenteditable="plaintext-only"]').first
            expect(paragraph).to_be_visible()
            paragraph.fill('Discard this edit')
            frame.get_by_role('button', name='取消编辑', exact=True).click()
            expect(frame.locator('article p').first).to_contain_text('Payment: 100 USD')
            page.get_by_role('button', name='编辑正文', exact=True).click()
            paragraph.fill('Payment: 100 USD222')
            frame.get_by_role('button', name='保存正文', exact=True).click()
            expect(frame.locator('article p').first).to_contain_text('Payment: 100 USD222')
            expect(frame.locator('#save-edit')).to_be_hidden()
            page.reload()
            expect(frame.locator('article p').first).to_contain_text('Payment: 100 USD222')
            expect(frame.locator('article table')).to_contain_text('Delivery terms')
            # Stale review results must not block repeated manual editing.
            edit_clause = page.get_by_role('button', name='编辑条款', exact=True).first
            expect(edit_clause).to_be_enabled()
            for value in ['Payment: 100 USD222333', 'Payment: 100 USD222333444']:
                edit_clause.click()
                editor = page.locator('.fixed textarea').last
                expect(editor).to_have_value('Payment: 100 USD222' if value == 'Payment: 100 USD222333' else 'Payment: 100 USD222333')
                editor.fill(value)
                page.get_by_role('button', name='保存条款', exact=True).click()
                expect(frame.locator('article p').first).to_contain_text(value)
                expect(frame.locator('.lexis-located')).to_have_text(value)
                page.reload()
                expect(frame.locator('article p').first).to_contain_text(value)
            expect(edit_clause).to_be_enabled()
            page.get_by_role('button', name='编辑正文', exact=True).click()
            frame.locator('[contenteditable="plaintext-only"]').last.fill('Delivery terms updated')
            frame.get_by_role('button', name='保存正文', exact=True).click()
            located = frame.locator('.lexis-located')
            expect(located).to_have_text('Delivery terms updated')
            expect(frame.locator('#locate-status')).to_have_text('已定位到刚修改的位置')
            assert located.evaluate('(el) => { const r=el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }')
            held = []
            def delay_first_handling(route):
                if not held:
                    held.append(route)
                else:
                    route.continue_()
            page.route('**/api/runs/*/handling', delay_first_handling)
            with page.expect_request('**/api/runs/*/handling'):
                page.get_by_role('button', name='不采纳', exact=True).first.click()
            page.get_by_role('button', name='待复核', exact=True).first.click()
            response = page.request.fetch(held[0].request)
            held[0].fulfill(response=response)
            page.get_by_role('button', name='保存', exact=True).click()
            expect(page.get_by_text('工作内容已保存', exact=True)).to_be_visible()
            card = page.locator('#card-'+result['issues'][0]['id'])
            expect(card.get_by_text('处理状态：待复核', exact=True)).to_be_visible()
            saved = page.request.get(base+'/api/tasks/'+task['id']).json()['run']
            assert saved['decisions'][result['issues'][0]['id']] == 'needs_review'
            page.unroute('**/api/runs/*/handling', delay_first_handling)
            for label, state in [('不采纳', 'rejected'), ('待复核', 'needs_review'), ('重置状态', 'pending')]:
                button = page.get_by_role('button', name=label, exact=True).first
                expect(button).to_be_enabled()
                with page.expect_response(lambda response: '/handling' in response.url and response.request.method == 'PUT'):
                    button.click()
                expect(button).to_have_attribute('aria-pressed', 'true')
                saved = page.request.get(base+'/api/tasks/'+task['id']).json()['run']
                assert saved['decisions'][result['issues'][0]['id']] == state
                page.reload()
                expect(page.get_by_role('button', name=label, exact=True).first).to_be_enabled()


            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
