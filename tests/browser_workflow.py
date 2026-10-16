"""Optional browser regression. Start an isolated service on port 8010 first."""
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

base = 'http://127.0.0.1:8010'
output = Path('artifacts')
output.mkdir(exist_ok=True)
name = '浏览器回归 ' + uuid4().hex[:8]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1600, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base)
    expect(page.get_by_role('heading', name='新建合同审查')).to_be_visible()
    expect(page.get_by_role('button', name='进入工作台核对合同')).to_be_disabled()
    page.get_by_role('button', name='快速审查 基础规则与关键风险').click()
    page.get_by_role('button', name='📑 示例合同').click()
    page.get_by_role('button', name='数字化营销与技术运营商务合作合同 示例 商务合作合同 (技术运营与营销推广) · 1156 字').click()
    page.get_by_role('textbox', name='合同名称', exact=True).fill(name)
    page.get_by_role('button', name='进入工作台核对合同').click()
    page.wait_for_url('**/workbench?task=*')
    page.get_by_role('button', name='开始审查', exact=True).click()
    expect(page.get_by_role('button', name='重新审查', exact=True)).to_be_visible(timeout=30000)
    page.get_by_role('button', name='采纳此项修订').first.click()
    page.get_by_role('textbox', name='条目处理备注').first.fill('回归测试备注')
    page.get_by_role('button', name='保存', exact=True).click()
    expect(page.get_by_text('工作内容已保存', exact=True)).to_be_visible()
    page.reload()
    expect(page.get_by_role('button', name='撤销采纳')).to_have_count(1)
    expect(page.get_by_role('textbox', name='条目处理备注').first).to_have_value('回归测试备注')
    page.get_by_role('button', name='重新审查', exact=True).click()
    expect(page.get_by_role('combobox', name='审查历史版本').locator('option')).to_have_count(2, timeout=30000)
    page.get_by_role('link', name='审查记录', exact=True).click()
    expect(page.get_by_role('table')).to_contain_text(name)
    assert not errors, errors
    browser.close()
    print('Browser regression passed. Synthetic records remain in the isolated test database.')
