import socket
import threading
from pathlib import Path
import uvicorn
from playwright.sync_api import sync_playwright,expect
from backend import main
from test_web_security import accounts


def test_web_login_admin_and_server_draft_recovery(accounts,monkeypatch):
    sock=socket.socket();sock.bind(('127.0.0.1',0))
    base=f'http://127.0.0.1:{sock.getsockname()[1]}'
    monkeypatch.setenv('LEXIS_ALLOWED_ORIGINS',base)
    server=uvicorn.Server(uvicorn.Config(main.app,log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def login(name,password):
                page.goto(base+'/login')
                page.get_by_label('账号',exact=True).fill(name)
                page.get_by_label('密码',exact=True).fill(password)
                page.get_by_role('button',name='登录',exact=True).click()
                page.wait_for_url(base+'/')
            login('admin','initial-admin-password')
            page.get_by_role('link',name='账号管理',exact=True).click()
            expect(page.get_by_role('heading',name='账号管理',exact=True)).to_be_visible()
            expect(page.get_by_role('button',name='alice alice')).to_be_visible()
            page.get_by_role('button',name='退出登录',exact=True).click()
            page.wait_for_url('**/login')
            login('alice','personal-password-alice')
            expect(page.get_by_role('link',name='账号管理',exact=True)).to_have_count(0)
            page.goto(base+'/reviews/new')
            expect(page.get_by_role('button',name='进入工作台核对合同')).to_be_visible()
            page.get_by_label('自定义审查要求（Prompt）',exact=True).fill('核对付款期限及验收安排')
            page.wait_for_function("document.body.innerText.includes('已保存')")
            page.wait_for_url('**/*copy=*')
            recovery_url=page.url
            assert page.evaluate("sessionStorage.getItem('LEXIS_HOME_DRAFT')") is None
            page.screenshot(path='artifacts/web-draft-saved.png',full_page=True)
            context.clear_cookies()
            page.evaluate('localStorage.clear();sessionStorage.clear()')
            login('alice','personal-password-alice')
            page.goto(recovery_url)
            expect(page.get_by_label('自定义审查要求（Prompt）',exact=True)).to_have_value('核对付款期限及验收安排')
            page.goto(base+'/drafting/new')
            page.get_by_label('合同名称',exact=False).fill('服务器起草需求')
            page.wait_for_function("document.body.innerText.includes('已保存')")
            url=page.url;page.reload()
            expect(page.get_by_label('合同名称',exact=False)).to_have_value('服务器起草需求')
            assert 'copy=' in url
            assert page.evaluate("sessionStorage.getItem('contract_drafting_new_brief')") is None
            assert not errors,errors
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10);sock.close()
