"""A background shorthand must never reset the shared select-chevron geometry."""
from playwright.sync_api import sync_playwright, expect
from test_functional_completeness import client, seed
from test_ui_composition import live_server


def test_select_chevrons_do_not_tile_after_workbench_styles_load(client):
    task, run = seed(client)
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1536,'height':900})
        errors=[]
        page.on('pageerror', lambda error:errors.append(str(error)))
        def check_selects():
            styles = page.locator('select:not([multiple])').evaluate_all('''elements => elements.map(el => {
                const s=getComputedStyle(el); return {repeat:s.backgroundRepeat,size:s.backgroundSize,position:s.backgroundPosition,appearance:s.appearance,image:s.backgroundImage};
            })''')
            assert styles
            for style in styles:
                assert style['repeat'] == 'no-repeat', style
                assert style['size'] == '14px 14px', style
                assert '10px' in style['position'], style
                assert style['appearance'] == 'none', style
                assert 'data:image/svg+xml' in style['image'], style
        for route in ['/', '/records', '/checklists']:
            page.goto(base + route)
            if route == '/' and page.locator('select').count() == 0:
                page.get_by_role('button', name='AI 智能全面审查').click()
            expect(page.locator('select').first).to_be_visible()
            check_selects()
        page.goto(base+'/workbench?task='+task['id'])
        page.locator('.wb-functional-overview > summary').click()
        expect(page.get_by_label('审查历史版本',exact=True)).to_be_visible()
        expect(page.get_by_label('筛选风险等级')).to_be_visible()
        check_selects()
        page.get_by_label('筛选风险等级').select_option('critical')
        expect(page.get_by_label('筛选风险等级')).to_have_value('critical')
        page.screenshot(path='artifacts/selects-workbench-fixed.png')
        page.get_by_role('button',name='审查意见书',exact=True).click()
        expect(page.get_by_label('意见书范围')).to_be_visible()
        check_selects()
        page.get_by_label('意见书范围').select_option('applied_report')
        expect(page.get_by_label('意见书范围')).to_have_value('applied_report')
        expect(page.locator('.wb-report-metadata')).to_contain_text('仅已采纳意见')
        page.screenshot(path='artifacts/selects-report-fixed.png')
        assert not errors,errors
        browser.close()
