import socket
import threading
from contextlib import contextmanager

import pytest
import uvicorn
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright

from backend.main import app
from backend.ui import PORTAL_PAGES


@contextmanager
def live_server():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{port}'
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_spa_history_fallback_and_assets():
    with TestClient(app) as client:
        index = client.get('/').text
        assert '/assets/index-' in index
        assert '/static/portal.js' not in index
        for path in [*PORTAL_PAGES, '/workbench', '/workbench.html', '/unknown-page']:
            response = client.get(path)
            assert response.status_code == 200
            assert response.text == index
            assert response.headers['cache-control'] == 'no-store'
        import re
        asset = re.search(r'src="([^"]+\.js)"', index)[1]
        assert client.get(asset).status_code == 200
        assert client.get('/api/no-such-endpoint').status_code == 404
        assert client.get('/assets/no-such-file.js').status_code == 404


def test_missing_build_explains_how_to_start(tmp_path, monkeypatch):
    from backend import ui
    monkeypatch.setattr(ui, 'DIST', tmp_path)
    with TestClient(app) as client:
        assert client.get('/').status_code == 503
        assert 'npm' in client.get('/').json()['detail']


def test_navigation_keeps_document_layout_forms_and_history(isolated_workspace):
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        errors, documents = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: documents.append(request.url) if request.is_navigation_request() and request.frame == page.main_frame else None)
        page.goto(base)
        expect(page.get_by_role('heading', name='新建合同审查', exact=True)).to_be_visible()
        page.evaluate("window.spaMarker = 'same-document'; window.shellHeader = document.querySelector('.portal-header')")
        page.get_by_role('button', name='✍️ 粘贴正文', exact=True).click()
        page.get_by_label('合同正文', exact=True).fill('第一条 验收后付款。')
        page.get_by_placeholder('填写便于识别的合同名称').fill('保留中的审查表单')
        nav = page.locator('.portal-sidebar nav')
        for name, heading in [('审查记录','审查记录'),('业务分类维护','业务分类维护'),('审查清单','企业审查清单')]:
            nav.get_by_role('link', name=name, exact=True).click()
            expect(page.get_by_role('heading', name=heading, exact=True)).to_be_visible()
            assert page.evaluate('window.spaMarker') == 'same-document'
            assert page.evaluate("window.shellHeader === document.querySelector('.portal-header')")
        page.go_back()
        expect(page.get_by_role('heading', name='业务分类维护', exact=True)).to_be_visible()
        page.go_forward()
        expect(page.get_by_role('heading', name='企业审查清单', exact=True)).to_be_visible()
        nav.get_by_role('link', name='开始', exact=True).click()
        expect(page.get_by_label('合同正文', exact=True)).to_have_text('第一条 验收后付款。')
        expect(page.get_by_placeholder('填写便于识别的合同名称')).to_have_value('保留中的审查表单')
        page.get_by_role('button', name='⚙ 模型配置', exact=True).click()
        expect(page.get_by_role('heading', name='模型配置', exact=True)).to_be_visible()
        page.get_by_role('button', name='关闭模型配置', exact=True).click()
        assert len(documents) == 1
        assert not errors
        browser.close()




def test_workbench_enters_leaves_and_switches_tasks_without_reload(isolated_workspace):
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.add_init_script("""
          window.messageListeners = new Set();
          const add = window.addEventListener.bind(window);
          const remove = window.removeEventListener.bind(window);
          window.addEventListener = (type, handler, options) => {
            if (type === 'message') window.messageListeners.add(handler);
            return add(type, handler, options);
          };
          window.removeEventListener = (type, handler, options) => {
            if (type === 'message') window.messageListeners.delete(handler);
            return remove(type, handler, options);
          };
        """)
        first = page.request.post(base+'/api/tasks', data={'title':'合同一', 'text':'第一条 验收合格后付款。', 'mode':'quick'}).json()
        second = page.request.post(base+'/api/tasks', data={'title':'合同二', 'text':'第二条 付款前提供发票。', 'mode':'quick'}).json()
        page.goto(base+'/records')
        expect(page.get_by_role('heading', name='审查记录', exact=True)).to_be_visible()
        page.evaluate("window.spaMarker = 'workbench-session'")
        page.get_by_role('row').filter(has=page.get_by_role('link', name='合同一', exact=True)).get_by_role('link', name='打开', exact=True).click()
        expect(page.get_by_role('heading', name='合同一', exact=True)).to_be_visible()
        expect(page.get_by_role('button', name='编辑正文', exact=True)).to_be_enabled()
        assert page.evaluate('window.spaMarker') == 'workbench-session'
        assert page.evaluate('window.messageListeners.size') == 2
        page.get_by_role('button', name='编辑正文', exact=True).click()
        page.get_by_label('编辑合同正文').fill('第一条 验收合格后30日付款。')
        page.get_by_role('button', name='保存正文', exact=True).click()
        page.get_by_role('link', name='返回主页', exact=True).click()
        expect(page.get_by_role('heading', name='审查条件', exact=True)).to_be_visible()
        assert page.evaluate('window.messageListeners.size') == 0
        assert page.request.get(base+'/api/tasks/'+first['id']).json()['text'] == '第一条 验收合格后30日付款。'
        page.go_back()
        expect(page.get_by_role('heading', name='合同一', exact=True)).to_be_visible()
        # A second in-app task link must create a fresh workbench session.
        page.get_by_role('link', name='返回主页', exact=True).click()
        page.locator('.portal-sidebar nav').get_by_role('link', name='审查记录', exact=True).click()
        page.get_by_role('row').filter(has=page.get_by_role('link', name='合同二', exact=True)).get_by_role('link', name='打开', exact=True).click()
        expect(page.get_by_role('heading', name='合同二', exact=True)).to_be_visible()
        assert page.evaluate('window.spaMarker') == 'workbench-session'
        assert page.evaluate('window.messageListeners.size') == 2
        browser.close()



def test_first_workbench_save_assigns_task_without_remount(isolated_workspace):
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base+'/workbench')
        expect(page.get_by_role('button', name='编辑正文', exact=True)).to_be_enabled()
        page.evaluate("window.spaMarker = 'new-task-editor'")
        page.get_by_role('button', name='编辑正文', exact=True).click()
        page.get_by_label('合同名称', exact=True).fill('新任务首次保存')
        page.get_by_label('编辑合同正文', exact=True).fill('第一条 验收合格后付款。')
        page.get_by_role('button', name='保存正文', exact=True).click()
        page.get_by_role('button', name='保存', exact=True).click()
        page.wait_for_url('**/workbench?task=*')
        expect(page.get_by_role('heading', name='新任务首次保存', exact=True)).to_be_visible()
        assert page.evaluate('window.spaMarker') == 'new-task-editor'
        assert len(page.request.get(base+'/api/tasks').json()['items']) == 1
        page.get_by_role('link', name='返回主页', exact=True).click()
        expect(page.get_by_role('heading', name='审查条件', exact=True)).to_be_visible()
        assert not errors
        browser.close()
