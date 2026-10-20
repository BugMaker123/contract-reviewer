"""The progress UI shows observable review work while technical details stay in logs."""
import asyncio
import json
import subprocess
import threading

from playwright.sync_api import sync_playwright, expect
from backend import graph, workspace_api
from backend.review_progress import emit_progress
from test_ui_composition import live_server


def test_public_activity_ignores_raw_model_messages_and_deduplicates_events():
    script = '''
import assert from 'node:assert/strict';
import {reviewActivities} from './frontend/src/workbench/reviewActivity.js';
const trace = [
 {stage:'prepare',contract_chars:3000,detail:'SECRET'},
 {stage:'segment',segment_count:12,detail:'SECRET'},
 {stage:'review',detail:'SECRET request 1/4'},
 {stage:'waiting',detail:'SECRET waiting'},
 {stage:'retry',detail:'SECRET key'},
 {stage:'review',detail:'SECRET request 2/4'},
];
const result = reviewActivities(trace);
assert.equal(result.filter(x=>x.id==='review').length,1);
assert.ok(!JSON.stringify(result).includes('SECRET'));
assert.ok(result.some(x=>x.text.includes('12')));
assert.equal(reviewActivities([...trace,{stage:'analysis_summary'}],2).at(-1).id,'findings');
'''
    result = subprocess.run(['node','--input-type=module','-e',script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_browser_shows_actual_review_activity_before_findings(isolated_workspace, monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    release_analysis, release_result = threading.Event(), threading.Event()
    original = workspace_api.review_events

    async def events(snapshot, config):
        emit_progress('segment', '内部条款日志', segment_count=2)
        yield 'node_update', {'node':'segment_contract','log':{'detail':'已解析正文'}}
        emit_progress('review', 'MODEL_CALL_SECRET 第1/4次请求')
        emit_progress('waiting', 'MODEL_CALL_SECRET 等待模型')
        emit_progress('retry', 'MODEL_CALL_SECRET 重试')
        await asyncio.to_thread(release_analysis.wait, 10)
        emit_progress('analysis_summary', '已识别付款安排问题', title='付款期限不明确', clause='付款条款',
                      analysis='需明确付款期限及验收安排。', proposal='补充付款时间。', severity='warning',
                      provisional=True, attempt=1, index=1)
        await asyncio.to_thread(release_result.wait, 10)
        async for item in original(snapshot, config):
            yield item

    monkeypatch.setattr(workspace_api, 'review_events', events)
    try:
        with live_server() as base, sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width':1366,'height':768})
            errors=[]
            page.on('pageerror', lambda error:errors.append(str(error)))
            task = page.request.post(base+'/api/tasks',data={'title':'渐进分析验收','text':'第一条 交付设备。\n第二条 验收后付款。','mode':'quick','focus':'核对付款期限'}).json()
            page.goto(base+'/workbench?task='+task['id'])
            page.get_by_role('button',name='开始审查',exact=True).click()
            dialog = page.get_by_role('dialog',name='合同合规性审查分析')
            expect(page.get_by_label('审查动态')).to_contain_text('已开始全文研判')
            expect(page.locator('.review-activity-metrics')).to_contain_text('已整理 2 个条款')
            expect(page.locator('[data-public-analysis]')).to_have_count(0)
            expect(dialog).not_to_contain_text('MODEL_CALL_SECRET')
            expect(page.get_by_role('button',name='取消审查',exact=True)).to_be_in_viewport()
            page.screenshot(path='artifacts/review-activity-before-findings.png')
            release_analysis.set()
            expect(page.locator('[data-public-analysis]')).to_contain_text('付款期限不明确')
            expect(page.get_by_label('审查动态')).to_contain_text('已收到 1 条初步意见')
            expect(page.get_by_role('button',name='取消审查',exact=True)).to_be_visible()
            expect(dialog).not_to_contain_text('MODEL_CALL_SECRET')
            page.screenshot(path='artifacts/review-activity-first-finding.png')
            release_result.set()
            expect(page.get_by_role('button',name='查看审查修订稿',exact=True)).to_be_visible()
            stored = page.request.get(base+'/api/tasks/'+task['id']).json()['run']
            assert any('MODEL_CALL_SECRET' in event['detail'] for event in stored['audit_trace'])
            assert not errors, errors
            browser.close()
    finally:
        release_analysis.set()
        release_result.set()
