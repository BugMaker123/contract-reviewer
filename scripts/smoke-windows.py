"""Exercise the actual frozen executable with disposable data."""
import ctypes
from ctypes import wintypes
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

import httpx
from docx import Document

EXE = Path(__file__).resolve().parents[1] / 'artifacts/windows/LexisGraph/LexisGraph.exe'


def close(process):
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    @callback_type
    def callback(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == process.pid:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
        return True
    user32.EnumWindows(callback, 0)
    try:
        process.wait(timeout=20)
        assert process.returncode == 0, process.returncode
    finally:
        if process.poll() is None:
            process.kill()


with tempfile.TemporaryDirectory(prefix='lexis-exe-smoke-') as temporary:
    env = {**os.environ, 'LEXIS_DATA_DIR': temporary}
    env.pop('LEXIS_DB_PATH', None)
    for key in ('OPENAI_API_KEY', 'DEEPSEEK_API_KEY'):
        env.pop(key, None)
    for cycle in range(2):
        log = Path(temporary) / 'application.log'
        if log.exists():
            log.write_text('', encoding='utf-8')
        process = subprocess.Popen([str(EXE), '--no-browser'], env=env)
        try:
            with httpx.Client(trust_env=False, timeout=60) as client:
                for _ in range(150):
                    text = log.read_text(encoding='utf-8') if log.exists() else ''
                    urls = re.findall(r'Desktop URL: (http://127\.0\.0\.1:\d+)', text)
                    if urls:
                        url = urls[-1]
                        try:
                            if client.get(url + '/api/health').is_success:
                                break
                        except httpx.TransportError:
                            pass
                    if process.poll() is not None:
                        raise AssertionError(text)
                    time.sleep(0.2)
                else:
                    raise AssertionError(text)
                assert client.get(url + '/templates').status_code == 200
                assert client.get(url + '/static/vendor/tailwind.css').status_code == 200
                groups = client.get(url + '/api/template-groups').json()
                if cycle == 0:
                    assert groups == [], groups
                    group = client.post(url + '/api/template-groups', json={'name': 'EXE测试分组'}).json()
                    document = Document()
                    document.add_paragraph('甲方：测试公司；合同金额：100元。')
                    content = BytesIO()
                    document.save(content)
                    imported = client.post(url + '/api/contracts/import', files={'file': ('测试.docx', content.getvalue())})
                    assert imported.status_code == 200, imported.text
                    source = imported.json()
                    template = client.post(url + '/api/contract-templates', json={'name': 'EXE测试模板', 'group_id': group['id'], 'source_id': source['source_id']})
                    assert template.status_code == 200, template.text
                    downloaded = client.get(url + '/api/contract-templates/' + template.json()['id'] + '/download')
                    assert downloaded.content == content.getvalue()
                    text_import = client.post(url + '/api/contracts/import', files={'file': ('测试.txt', '测试文本合同'.encode())})
                    assert text_import.status_code == 200, text_import.text
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch()
                        page = browser.new_page(viewport={'width': 1440, 'height': 900})
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(url + '/templates')
                        page.get_by_text('EXE测试模板', exact=True).wait_for()
                        page.screenshot(path=str(EXE.parents[2] / 'windows-exe-smoke.png'), full_page=True)
                        assert not errors, errors
                        browser.close()
                else:
                    assert groups[0]['name'] == 'EXE测试分组', groups
                    assert client.get(url + '/api/contract-templates').json()['total'] == 1
                print(f'Cycle {cycle + 1}: startup, pages, persistence OK', flush=True)
        finally:
            close(process)
    parsed = subprocess.run([str(EXE), '--parse-document', '.txt'], input='中文解析'.encode(), capture_output=True, env=env, timeout=45)
    assert json.loads(parsed.stdout)['text'] == '中文解析', parsed.stderr
    print('Frozen DOCX/TXT parsing, import, original download, graceful exit and restart passed.', flush=True)
