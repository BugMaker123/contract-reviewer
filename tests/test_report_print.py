"""Verify printed pages, rather than only print-media DOM visibility."""
from io import BytesIO
from pypdf import PdfReader
from playwright.sync_api import sync_playwright, expect
from test_functional_completeness import client, seed
from test_ui_composition import live_server


def test_report_pdf_has_visible_directory_and_no_blank_pages(client):
    task, run = seed(client)
    for index in range(20):
        response = client.post('/api/runs/' + run['id'] + '/issues', json={
            'revision': run['revision'], 'title': f'付款条件核对 {index + 1}',
            'analysis': '付款期限与验收安排需要双方书面确认。' * 8,
            'evidence': '验收后30日付款。', 'severity': 'critical',
        })
        assert response.status_code == 200, response.text
        run = response.json()
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1536, 'height': 800})
        page.goto(base + '/workbench?task=' + task['id'])
        page.get_by_role('button', name='审查意见书', exact=True).click()
        expect(page.locator('.wb-report-directory a')).to_have_count(23)
        original_title = page.title()
        page.evaluate("window.print = () => { window.dispatchEvent(new Event('beforeprint')); window.capturedPrintTitle = document.title; window.dispatchEvent(new Event('afterprint')); }")
        page.get_by_role('button', name='打印 / 存为 PDF', exact=True).click()
        assert page.evaluate('window.capturedPrintTitle') == '功能闭环合同-审查意见书-第1次审查'
        assert page.title() == original_title
        page.emulate_media(media='print')
        expect(page.locator('.wb-report-directory')).to_be_visible()
        data = page.pdf(path='artifacts/report-print-regression.pdf', format='A4', print_background=True, outline=True)
        reader = PdfReader(BytesIO(data))
        texts = [pdf_page.extract_text() for pdf_page in reader.pages]
        assert '目录' in texts[0]
        assert '付款条件核对20' in ''.join(''.join(texts[:3]).split())
        assert all(len(text.strip()) > 20 for text in texts), [(i + 1, len(text)) for i, text in enumerate(texts)]
        assert any('合同审查意见书' in text for text in texts[1:])
        assert any(annotation.get_object().get('/Subtype') == '/Link' for pdf_page in reader.pages[:2] for annotation in pdf_page.get('/Annots', []))
        browser.close()
