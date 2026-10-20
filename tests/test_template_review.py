from io import BytesIO
import pytest
from docx import Document
from fastapi.testclient import TestClient
from backend.main import app
from backend import template_review


def upload(client, text):
    doc = Document()
    doc.add_paragraph(text)
    data = BytesIO()
    doc.save(data)
    return client.post('/api/contracts/import', files={'file': ('template.docx', data.getvalue())}).json()['source_id']


def setup_template(client):
    group = client.post('/api/template-groups', json={'name': '测试分组'}).json()
    source = upload(client, '甲方：____；期限：30日。')
    record = client.post('/api/contract-templates', json={'name': '模板', 'group_id': group['id'], 'source_id': source}).json()
    return record, '/api/contract-templates/' + record['id']


def region(**changes):
    return {'id': 'f1', 'name': '甲方', 'block_id': 'b0', 'start': 3, 'end': 7,
            'type': 'text', 'policy': 'conditional', 'confirmed': True, **changes}


def test_rules_publication_trial_and_replacement():
    with TestClient(app) as client:
        record, base = setup_template(client)
        detail = client.get(base+'/review').json()
        assert detail['blocks'][0]['text'] == '甲方：____；期限：30日。'
        assert client.put(base+'/review', json={'revision': 1, 'source_id': record['source_id'], 'fields': [region(), region(id='overlap', start=4)]}).status_code == 422
        saved = client.put(base+'/review', json={'revision': 1, 'source_id': record['source_id'], 'fields': [region()]}).json()
        assert saved['revision'] == 2
        assert client.put(base+'/review', json={'revision': 1, 'source_id': record['source_id'], 'fields': []}).status_code == 409
        published = client.post(base+'/publish', json={'revision': 2}).json()
        assert published['review_status'] == 'published'
        release = template_review.repo().get(published['release_id'], 'template_release')
        good = upload(client, '甲方：某某公司；期限：30日。')
        result = client.post(base+'/trial', json={'revision': 3, 'source_id': good}).json()
        assert result['result'] == 'PASS' and result['values'][0]['value'] == '某某公司'
        assert result['eligible_for_skip'] is False
        bad = upload(client, '甲方：某某公司；期限：60日。')
        assert client.post(base+'/trial', json={'revision': 3, 'source_id': bad}).json()['result'] == 'DIFFERENT'
        assert client.post(base+'/trial', json={'revision': 3, 'source_id': record['source_id']}).json()['result'] == 'DIFFERENT'
        client.put(base+'/review', json={'revision': 3, 'source_id': record['source_id'], 'fields': [region(confirmed=False)]})
        assert client.post(base+'/publish', json={'revision': 4}).status_code == 422
        assert template_review.repo().get(release['id'])['fields'][0]['confirmed'] is True
        updated = client.put(base, json={'name': '新模板', 'group_id': record['group_id'], 'source_id': good, 'revision': 4}).json()
        assert updated['review_status'] == 'draft'
        assert client.get(base+'/review').json()['fields'] == []
        assert len(client.get(base+'/review').json()['releases']) == 1


def test_ai_positions_validated_and_no_implicit_save(monkeypatch):
    async def fake_model(config, prompt):
        return {'fields': [{'name': '甲方', 'block_id': 'b0', 'text': '____', 'type': 'text'}]}
    monkeypatch.setattr(template_review, 'model_json', fake_model)
    with TestClient(app) as client:
        record, base = setup_template(client)
        result = client.post(base+'/extract-fields', json={'revision': 1}).json()
        assert result['fields'][0]['start'] == 3
        assert not result['fields'][0]['confirmed']
        assert result['fields'][0]['policy'] == 'manual'
        assert client.get(base+'/review').json()['fields'] == []
        async def invalid_model(config, prompt):
            return {'fields': [{'name': '编造', 'block_id': 'b0', 'text': '不存在'}]}
        monkeypatch.setattr(template_review, 'model_json', invalid_model)
        assert client.post(base+'/extract-fields', json={'revision': 1}).status_code == 422


def test_numeric_and_structure_matching():
    before = [{'id': 'b0', 'text': '天数：____天', 'section': '正文', 'kind': 'paragraph'}]
    fields = [template_review.Region(**region(type='integer', minimum=1, maximum=30)).model_dump()]
    assert template_review.compare_blocks(before, [{**before[0], 'text': '天数：20天'}], fields)['result'] == 'PASS'
    assert template_review.compare_blocks(before, [{**before[0], 'text': '天数：60天'}], fields)['result'] == 'DIFFERENT'
    assert template_review.compare_blocks(before, [], fields)['result'] == 'UNDETERMINED'
    fields[0]['policy'] = 'manual'
    assert template_review.compare_blocks(before, [{**before[0], 'text': '天数：20天'}], fields)['result'] == 'DIFFERENT'


def test_review_browser_manual_mark_persist_publish():
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    with TestClient(app) as client:
        record, base = setup_template(client)
    with live_server() as address, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1700, 'height': 1100})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(address+'/templates/'+record['id']+'/review')
        expect(page.get_by_role('heading', name='模板')).to_be_visible()
        expect(page.locator('.portal-sidebar')).to_have_count(0)
        assert page.locator('.tr-workspace').bounding_box()['y'] <= 150
        expect(page.get_by_role('link', name='返回主页', exact=True)).to_have_attribute('href', '/')
        page.get_by_role('button', name='手动添加', exact=True).click()
        dialog = page.get_by_role('dialog')
        dialog.get_by_label('原文位置', exact=True).select_option('b0')
        dialog.get_by_label('开始位置', exact=True).fill('4')
        dialog.get_by_label('结束位置（包含）', exact=True).fill('7')
        dialog.get_by_role('button', name='保存位置').click()
        page.get_by_label('字段名称', exact=True).fill('甲方名称')
        page.get_by_label('免审处理', exact=True).select_option('conditional')
        page.get_by_role('button', name='确认并下一项').click()
        page.get_by_role('button', name='保存草稿').click()
        expect(page.locator('.tr-foot span')).to_have_text('已保存')
        page.reload()
        expect(page.locator('.tr-field')).to_contain_text('甲方名称')
        page.get_by_role('button', name='发布版本', exact=True).click()
        page.get_by_role('dialog').get_by_role('button', name='确认', exact=True).click()
        expect(page.locator('.tr-heading .tr-status-badge')).to_have_text('已发布')
        assert not errors
        browser.close()


def test_ai_partial_results_and_typographic_location(monkeypatch):
    async def fake_model(config, prompt):
        return {'fields': [
            {'name': '甲方', 'block_id': 'b0', 'text': '＿＿＿＿'},
            {'name': '重复', 'block_id': 'b0', 'text': '____'},
            {'name': '编造', 'block_id': 'b0', 'text': '不存在'},
            {'name': '坏类型', 'block_id': 'b0', 'text': '30', 'type': 'text/integer'},
        ]}
    monkeypatch.setattr(template_review, 'model_json', fake_model)
    with TestClient(app) as client:
        record, base = setup_template(client)
        response = client.post(base+'/extract-fields', json={'revision': 1})
        assert response.status_code == 200
        data = response.json()
        assert len(data['fields']) == 1
        assert data['fields'][0]['start'] == 3 and data['fields'][0]['end'] == 7
        assert data['fields'][0]['policy'] == 'manual' and not data['fields'][0]['confirmed']
        assert len(data['skipped']) == 3
        assert client.get(base+'/review').json()['fields'] == []


def test_ai_failure_distinguished_and_draft_preserved(monkeypatch):
    async def failed_model(config, prompt):
        raise RuntimeError('provider-private-key')
    monkeypatch.setattr(template_review, 'model_json', failed_model)
    with TestClient(app) as client:
        record, base = setup_template(client)
        client.put(base+'/review', json={'revision': 1, 'source_id': record['source_id'], 'fields': [region()]})
        response = client.post(base+'/extract-fields', json={'revision': 2})
        assert response.status_code == 502
        assert '模型调用失败' in response.json()['detail']
        assert 'provider-private-key' not in response.text
        assert len(client.get(base+'/review').json()['fields']) == 1


def test_ai_ambiguous_normalization_not_guessed(monkeypatch):
    async def fake_model(config, prompt):
        return {'fields': [{'name': '甲方', 'block_id': 'b0', 'text': '＿＿'}]}
    monkeypatch.setattr(template_review, 'model_json', fake_model)
    with TestClient(app) as client:
        record, base = setup_template(client)
        response = client.post(base+'/extract-fields', json={'revision': 1})
        assert response.status_code == 422
        assert '无法唯一定位' in response.json()['detail']


def test_review_browser_extraction_feedback(monkeypatch):
    import asyncio
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect

    async def fake_model(config, prompt):
        await asyncio.sleep(0.6)
        return {'fields': [
            {'name': '甲方名称', 'block_id': 'b0', 'text': '____'},
            {'name': '无法定位字段', 'block_id': 'b0', 'text': '不在原文中'},
        ]}
    monkeypatch.setattr(template_review, 'model_json', fake_model)
    with TestClient(app) as client:
        record, base = setup_template(client)
    with live_server() as address, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1700, 'height': 1100})
        page.goto(address+'/templates/'+record['id']+'/review')
        page.get_by_role('button', name='AI 提取', exact=True).click()
        page.get_by_role('dialog').get_by_role('button', name='确认', exact=True).click()
        expect(page.locator('.tr-extraction-status')).to_contain_text('正在识别合同填写区域')
        expect(page.locator('.tr-field')).to_contain_text('甲方名称')
        expect(page.locator('.tr-extraction-status')).to_contain_text('已识别 1 个填写区域')
        page.locator('.tr-extraction-status summary').click()
        expect(page.locator('.tr-extraction-status')).to_contain_text('无法定位字段')
        expect(page.locator('.tr-mark')).to_have_text('____')
        page.get_by_label('搜索填写区域').fill('找不到')
        expect(page.locator('.tr-no-matches')).to_have_text('没有匹配的填写区域')
        page.get_by_label('搜索填写区域').fill('')
        expect(page.locator('.tr-field')).to_have_count(1)
        page.locator('.tr-view-options > summary').click()
        page.get_by_label('显示段落位置').check()
        expect(page.locator('.tr-block-label').first).to_be_visible()
        page.get_by_label('显示段落位置').uncheck()
        expect(page.locator('.tr-block-label')).to_have_count(0)
        expect(page.locator('.tr-foot span')).to_have_text('尚未保存')
        browser.close()
