from fastapi.testclient import TestClient
from backend.main import app


def test_categories_and_selected_checklist_snapshot():
    with TestClient(app) as client:
        category = client.post('/api/categories', json={'name': '技术开发', 'code': 'TECH_DEV'}).json()
        assert client.post('/api/categories', json={'name': '其他', 'code': 'TECH_DEV'}).status_code == 409
        assert client.put('/api/categories/' + category['id'], json={**category, 'name': '技术实施'}).status_code == 200
        assert client.put('/api/categories/' + category['id'], json=category).status_code == 409
        items = [{'id': str(i), 'title': '付款' + str(i), 'requirement': '验收后付款', 'operator': 'contains_all', 'keywords': ['验收']} for i in range(2)]
        checklist = client.post('/api/checklists', json={'name': '技术标准', 'category_id': category['id'], 'items': items, 'published': True}).json()
        body = {'title': '测试合同', 'text': '验收后付款', 'mode': 'checklist', 'checklist_id': checklist['id'], 'checklist_item_ids': ['1']}
        task = client.post('/api/tasks', json=body).json()
        assert [item['id'] for item in task['checklist']['items']] == ['1']
        assert len(client.get('/api/checklists').json()['items'][0]['items']) == 2
        assert client.post('/api/tasks', json={**body, 'checklist_item_ids': []}).status_code == 422
        assert client.post('/api/tasks', json={**body, 'checklist_item_ids': ['unknown']}).status_code == 422
        updated = client.put('/api/checklists/' + checklist['id'], json={**checklist, 'items': [items[0]]})
        assert updated.status_code == 200
        assert client.get('/api/tasks/' + task['id']).json()['checklist']['items'][0]['id'] == '1'


def test_category_and_checklist_browser(isolated_workspace):
    import socket
    import threading
    import uvicorn
    from playwright.sync_api import sync_playwright, expect
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            base = f'http://127.0.0.1:{sock.getsockname()[1]}'
            page.goto(base + '/categories')
            page.get_by_role('button', name='＋ 新增业务分类').click()
            page.get_by_label('分类名称', exact=True).fill('技术开发与实施类')
            page.get_by_label('分类编码', exact=True).fill('TECH_DEV')
            page.get_by_role('button', name='保存分类', exact=True).click()
            expect(page.get_by_role('cell', name='技术开发与实施类', exact=True)).to_be_visible()
            category = page.request.get(base + '/api/categories').json()['items'][0]
            checklist = page.request.post(base + '/api/checklists', data={'name': '技术审查标准', 'category_id': category['id'], 'published': True, 'items': [{'id': str(i), 'title': title, 'requirement': '检查合同约定是否完整', 'severity': 'critical'} for i, title in enumerate(['付款与验收条件', '违约责任上限'])]}).json()
            page.goto(base + '/?checklist=' + checklist['id'])
            expect(page.get_by_text('已勾选 2 项', exact=True)).to_be_visible()
            page.locator('.checklist-selection-summary').click()
            page.get_by_role('button', name='取消全选', exact=True).click()
            expect(page.get_by_text('已勾选 0 项', exact=True)).to_be_visible()
            expect(page.get_by_role('button', name='进入工作台核对合同')).to_be_disabled()
            page.locator('.checklist-option input').first.check()
            expect(page.get_by_text('已勾选 1 项', exact=True)).to_be_visible()
            page.get_by_role('tab', name='粘贴正文', exact=True).click()
            page.get_by_label('合同正文', exact=True).fill('第一条 付款与验收，验收合格后付款。')
            page.locator('.review-contract-name input').fill('技术服务合同')
            expect(page.locator('.review-prompt-field')).to_have_count(0)
            mode = page.locator('select').filter(has=page.locator('option[value="deep"]'))
            mode.select_option('deep')
            expect(page.locator('.checklist-selection')).to_have_count(0)
            page.locator('.review-prompt-field textarea').fill('重点检查知识产权归属')
            mode.select_option('checklist')
            expect(page.locator('.review-prompt-field')).to_have_count(0)
            mode.select_option('deep')
            expect(page.locator('.review-prompt-field textarea')).to_have_value('重点检查知识产权归属')
            mode.select_option('checklist')
            page.get_by_role('button', name='进入工作台核对合同').click()
            page.wait_for_url('**/workbench?task=*')
            task_id = page.url.split('task=')[1]
            task = page.request.get(base + '/api/tasks/' + task_id).json()
            assert len(task['checklist']['items']) == 1
            assert task['focus'] == ''
            assert not errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_uploaded_contract_opens_workbench(isolated_workspace):
    import socket
    import threading
    import uvicorn
    from playwright.sync_api import sync_playwright, expect

    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1440, 'height': 900})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            base = f'http://127.0.0.1:{sock.getsockname()[1]}'
            page.goto(base + '/')
            page.get_by_role('button', name='AI 智能全面审查').click()
            page.locator('input[type="file"]').first.set_input_files({
                'name': '采购协议.txt', 'mimeType': 'text/plain',
                'buffer': '第一条 采购价款为100元，验收后付款。'.encode('utf-8'),
            })
            expect(page.get_by_role('button', name='预览合同')).to_be_visible()
            page.get_by_role('button', name='预览合同').click()
            expect(page.get_by_title('合同原件预览')).to_be_visible()
            page.get_by_role('button', name='关闭预览').click()
            page.get_by_label('自定义审查要求（Prompt）', exact=True).fill('核对付款与税费约定')
            page.evaluate('''() => {
                const draft = JSON.parse(sessionStorage.getItem('LEXIS_HOME_DRAFT'));
                draft.type = '';
                draft.requirements = [{ id: 'custom-empty', text: '', priority: 'required', source: '用户要求' }];
                sessionStorage.setItem('LEXIS_HOME_DRAFT', JSON.stringify(draft));
            }''')
            page.reload()
            page.get_by_role('button', name='AI 智能全面审查').click()
            expect(page.get_by_role('button', name='预览合同')).to_be_visible()
            page.get_by_role('button', name='进入工作台核对合同').click()
            page.wait_for_url('**/workbench?task=*')
            assert not errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
