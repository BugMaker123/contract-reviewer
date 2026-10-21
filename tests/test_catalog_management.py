from fastapi.testclient import TestClient
from backend.main import app


def test_catalog_server_pagination_filters_and_delete_snapshots():
    with TestClient(app) as client:
        categories = [client.post('/api/categories', json={'name': f'分类{i:02}', 'code': f'CAT_{i}', 'sort_order': i}).json() for i in range(23)]
        page = client.get('/api/categories', params={'page': 2, 'page_size': 10}).json()
        assert page['total'] == 23 and page['page'] == 2 and len(page['items']) == 10
        assert page['items'][0]['id'] == categories[10]['id']
        assert client.get('/api/categories?page=99&page_size=10').json()['page'] == 3
        assert client.get('/api/categories?page=1&q=CAT_22').json()['total'] == 1
        assert client.get('/api/categories?page=0').status_code == 422
        assert client.get('/api/checklists?page=1&page_size=101').status_code == 422
        items = [{'id': 'point', 'title': '验收条件', 'requirement': '验收合格后付款'}]
        lists = [client.post('/api/checklists', json={'name': f'清单{i:02}', 'category_id': categories[0]['id'], 'items': items, 'published': True}).json() for i in range(12)]
        client.post('/api/checklists', json={'name': '其他分类', 'category_id': categories[1]['id'], 'items': items})
        result = client.get('/api/checklists', params={'page': 2, 'page_size': 10, 'category_id': categories[0]['id'], 'q': '验收', 'published': True, 'archived': False}).json()
        assert result['total'] == 12 and len(result['items']) == 2
        assert result['items'][0]['item_count'] == 1 and 'items' not in result['items'][0]
        counts = client.get('/api/categories?page=1').json()['items']
        assert counts[0]['checklist_count'] == 12
        category_url = '/api/categories/' + categories[0]['id']
        assert client.delete(category_url, params={'revision': 1}).status_code == 409
        checklist = lists[0]
        url = '/api/checklists/' + checklist['id']
        task = client.post('/api/tasks', json={'title': '测试合同', 'text': '验收后付款', 'mode': 'checklist', 'checklist_id': checklist['id']}).json()
        assert client.get(url).json()['items'] == checklist['items']
        assert client.delete(url, params={'revision': 999}).status_code == 409
        assert client.delete(url, params={'revision': 1}).status_code == 200
        assert client.get(url).status_code == 404
        assert client.get('/api/tasks/' + task['id']).json()['checklist']['items'] == checklist['items']
        assert client.delete('/api/categories/' + categories[-1]['id'], params={'revision': 1}).status_code == 200
        assert client.get('/api/categories/' + categories[-1]['id']).status_code == 404
        assert client.get('/api/drafts').status_code == 404
        assert client.post('/api/drafts', json={'title': 'retired'}).status_code == 405
        assert not any(getattr(route, 'path', '').startswith('/api/drafts') for route in app.routes)


def test_catalog_browser_crud_and_category_navigation(isolated_workspace):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda err: errors.append(str(err)))
        for i in range(12):
            page.request.post(base + '/api/categories', data={'name': f'业务{i:02}', 'code': f'BIZ_{i}', 'sort_order': i})
        page.goto(base + '/categories')
        expect(page.locator('tbody tr')).to_have_count(10)
        expect(page.locator('.portal-sidebar').get_by_text('合同起草', exact=True)).to_have_count(0)
        expect(page.locator('.portal-sidebar').get_by_text('起草记录', exact=True)).to_have_count(0)
        page.get_by_role('button', name='下一页', exact=True).click()
        expect(page.locator('tbody tr')).to_have_count(2)
        page.get_by_label('搜索业务分类').fill('业务00')
        expect(page.locator('tbody tr')).to_have_count(1)
        page.get_by_role('link', name='添加清单', exact=True).click()
        expect(page.get_by_role('heading', name='创建审查清单', exact=True)).to_be_visible()
        expect(page.locator('.modal select').first.locator('option:checked')).to_have_text('业务00')
        page.get_by_placeholder('如：采购合同审查要求').fill('业务00付款标准')
        page.locator('.checklist-item-advanced > summary').first.click()
        page.get_by_label('检查项标题', exact=True).fill('付款时间')
        page.get_by_label('检查项要求', exact=True).fill('验收合格后付款')
        page.get_by_role('button', name='保存并启用', exact=True).click()
        expect(page.get_by_role('cell', name='业务00付款标准', exact=True)).to_be_visible()
        page.get_by_role('button', name='查看', exact=True).click()
        expect(page.get_by_role('dialog', name='清单详情')).to_be_visible()
        page.get_by_role('button', name='关闭清单详情').click()
        page.get_by_role('button', name='编辑清单', exact=True).click()
        page.get_by_placeholder('如：采购合同审查要求').fill('更新后的标准')
        page.get_by_role('button', name='保存并启用', exact=True).click()
        expect(page.get_by_role('cell', name='更新后的标准', exact=True)).to_be_visible()
        page.get_by_role('button', name='删除', exact=True).click()
        page.get_by_role('button', name='确认删除', exact=True).click()
        expect(page.get_by_role('cell', name='更新后的标准', exact=True)).to_have_count(0)
        page.locator('.portal-sidebar').get_by_role('link', name='业务分类维护').click()
        expect(page.locator('tbody tr')).to_have_count(1)
        page.get_by_role('button', name='编辑', exact=True).click()
        page.get_by_label('分类名称', exact=True).fill('业务00更新')
        page.get_by_role('button', name='保存分类', exact=True).click()
        expect(page.get_by_role('cell', name='业务00更新', exact=True)).to_be_visible()
        page.get_by_role('button', name='删除', exact=True).click()
        page.get_by_role('button', name='确认删除', exact=True).click()
        expect(page.locator('tbody tr')).to_have_count(0)
        page.goto(base + '/draft')
        expect(page.get_by_role('heading', name='页面不存在')).to_be_visible()
        assert not errors, errors
        browser.close()


def test_home_checklist_summary_restored_draft_and_selection(isolated_workspace):
    import json
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        lists = [page.request.post(base + '/api/checklists', data={
            'name': '首页清单' + str(index), 'published': True,
            'items': [{'id': 'payment', 'title': '付款', 'requirement': '验收后付款'}],
        }).json() for index in range(2)]
        draft = {'mode': 'checklist', 'title': '恢复中的合同', 'text': '第一条 验收后付款。',
                 'checklist_id': lists[0]['id'], 'checklist_item_ids': ['payment']}
        page.add_init_script('sessionStorage.setItem("LEXIS_HOME_DRAFT", ' + json.dumps(json.dumps(draft)) + ')')
        page.goto(base)
        page.get_by_role('button', name='AI 智能全面审查').click()
        expect(page.get_by_role('heading', name='新建合同审查', exact=True)).to_be_visible()
        expect(page.get_by_text('首页清单1 · 1 条要求', exact=True)).to_have_count(1)
        expect(page.get_by_role('button', name='进入工作台核对合同', exact=True)).to_be_enabled()
        page.locator('.checklist-picker select').last.select_option(lists[1]['id'])
        expect(page.locator('.checklist-selection')).to_contain_text('已勾选 1 项')
        page.get_by_role('button', name='进入工作台核对合同', exact=True).click()
        page.wait_for_url('**/workbench?task=*')
        task = page.request.get(base + '/api/tasks/' + page.url.split('task=')[1]).json()
        assert task['checklist']['id'] == lists[1]['id']
        assert task['text'] == draft['text']
        assert not errors, errors
        browser.close()
