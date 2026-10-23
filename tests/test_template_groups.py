from docx import Document
from io import BytesIO
from test_ui_composition import live_server
from playwright.sync_api import sync_playwright, expect


def test_template_groups_management_navigation_and_crud(isolated_workspace):
    with live_server() as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        # 1. 访问首页，从侧边栏导航点击进入“模板分组维护”
        page.goto(base + '/')
        nav_link = page.locator('.portal-sidebar').get_by_role('link', name='模板分组维护', exact=True)
        expect(nav_link).to_be_visible()
        nav_link.click()
        page.wait_for_url('**/template-groups')
        expect(page.get_by_role('heading', name='模板分组维护', exact=True)).to_be_visible()

        # 2. 点击“新建分组”
        page.get_by_role('button', name='新建分组', exact=True).click()
        dialog = page.get_by_role('dialog', name='新建模板分组')
        expect(dialog).to_be_visible()
        dialog.get_by_label('分组名称', exact=True).fill('法务合规组')
        dialog.get_by_placeholder('简要描述该分组所适用的合同类型').fill('合规风控审查专用')
        dialog.get_by_role('button', name='保存', exact=True).click()
        expect(dialog).to_have_count(0)

        # 3. 验证列表中出现新建的分组
        row = page.get_by_role('row').filter(has_text='法务合规组')
        expect(row).to_be_visible()
        expect(row).to_contain_text('合规风控审查专用')
        expect(row).to_contain_text('0 个模板')

        # 4. 编辑分组
        row.get_by_role('button', name='编辑', exact=True).click()
        edit_dialog = page.get_by_role('dialog', name='编辑模板分组')
        expect(edit_dialog).to_be_visible()
        edit_dialog.get_by_label('分组名称', exact=True).fill('法务合规更新组')
        edit_dialog.get_by_role('button', name='保存', exact=True).click()
        expect(edit_dialog).to_have_count(0)
        expect(page.get_by_text('法务合规更新组', exact=True)).to_be_visible()

        # 5. 点击“查看模板”，跳转到合同模板列表
        row_updated = page.get_by_role('row').filter(has_text='法务合规更新组')
        row_updated.get_by_role('button', name='查看模板', exact=True).click()
        page.wait_for_url('**/templates?group=*')
        expect(page.get_by_role('heading', name='合同模板', exact=True)).to_be_visible()
        # 页面顶部选中的分组应为该组
        expect(page.get_by_role('heading', name='法务合规更新组', exact=True)).to_be_visible()

        # 6. 返回分组维护页并删除该分组
        page.locator('.portal-sidebar').get_by_role('link', name='模板分组维护', exact=True).click()
        page.wait_for_url('**/template-groups')
        target_row = page.get_by_role('row').filter(has_text='法务合规更新组')
        target_row.get_by_role('button', name='删除', exact=True).click()
        del_dialog = page.get_by_role('dialog', name='删除模板分组')
        expect(del_dialog).to_be_visible()
        del_dialog.get_by_role('button', name='确认删除', exact=True).click()
        expect(del_dialog).to_have_count(0)
        expect(page.get_by_text('法务合规更新组', exact=True)).to_have_count(0)

        assert not errors, f'页面发生 JS 错误: {errors}'
        browser.close()
