import asyncio
import threading
import httpx
from playwright.sync_api import sync_playwright, expect
from backend import workspace_api
from test_ui_composition import live_server


def test_minimize_queued_task_leave_resume_and_finish_in_background(isolated_workspace, monkeypatch):
    filler_release=threading.Event(); review_release=threading.Event()
    async def events(snapshot,config):
        gate=filler_release if snapshot['title'].startswith('占位') else review_release
        await asyncio.to_thread(gate.wait, 25)
        yield 'complete', {'segments':[],'issues':[],'summary':{'verdict':'审查完成','critical_count':0,'warning_count':0,'info_count':0},'coverage':'测试审查'}
    monkeypatch.setattr(workspace_api,'review_events',events)
    try:
        with live_server() as base, sync_playwright() as p:
            with httpx.Client(base_url=base,timeout=10,trust_env=False) as client:
                for index in range(5):
                    task=client.post('/api/tasks',json={'title':f'占位{index}','text':'第一条 交付设备。第二条 验收付款。','mode':'quick'}).json()
                    with client.stream('POST','/api/tasks/'+task['id']+'/review/stream',json={'model_config_data':{'api_key':'ui-test-key'}}) as response:
                        assert response.status_code==200
                        for line in response.iter_lines():
                            if line.startswith('data:'):break
                task=client.post('/api/tasks',json={'title':'排队与最小化验收','text':'第一条 交付设备。第二条 验收付款。','mode':'quick'}).json()
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1536,'height':900})
            page.add_init_script("localStorage.setItem('LEXIS_API_KEY','ui-test-key')")
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base+'/workbench?task='+task['id'])
            page.get_by_role('button',name='开始审查',exact=True).click()
            dialog=page.get_by_role('dialog',name='合同合规性审查分析')
            expect(dialog).to_contain_text('排队第 1 位')
            expect(page.get_by_role('button',name='取消排队')).to_be_visible()
            page.screenshot(path='artifacts/review-queued-dialog.png')
            page.get_by_role('button',name='最小化审查进度').click()
            expect(dialog).to_have_count(0)
            expect(page.get_by_role('button',name='恢复审查进度')).to_contain_text('审查排队中')
            page.screenshot(path='artifacts/review-minimized-queued.png')
            page.get_by_role('link',name='退出工作台',exact=True).click()
            expect(page.get_by_role('heading',name='新建合同审查')).to_be_visible()
            saved=page.request.get(base+'/api/tasks/'+task['id']).json()
            assert saved['status']=='queued' and len(saved['runs'])==1
            page.get_by_role('link',name='审查记录',exact=True).click()
            row=page.get_by_role('row').filter(has_text='排队与最小化验收')
            expect(row).to_contain_text('排队中')
            row.get_by_role('link',name='打开',exact=True).click()
            page.get_by_role('button',name='查看后台进度',exact=True).click()
            expect(dialog).to_contain_text('排队第 1 位')
            page.get_by_role('button',name='最小化审查进度').click()
            filler_release.set()
            expect(page.get_by_role('button',name='恢复审查进度')).to_contain_text('审查正在后台进行',timeout=15000)
            review_release.set()
            expect(page.get_by_role('button',name='恢复审查进度')).to_contain_text('审查已完成',timeout=15000)
            page.get_by_role('button',name='恢复审查进度').click()
            expect(page.get_by_role('button',name='查看审查修订稿')).to_be_visible()
            saved=page.request.get(base+'/api/tasks/'+task['id']).json()
            assert saved['status']=='pending_review' and len(saved['runs'])==1
            assert not errors,errors
            browser.close()
    finally:
        filler_release.set();review_release.set()

