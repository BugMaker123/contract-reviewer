import re
from io import BytesIO
from docx import Document
from fastapi.testclient import TestClient
from backend.main import app
from backend import template_review
from test_template_review import setup_template


def upload_rows(client, values):
    document=Document()
    for i,value in enumerate(values): document.add_paragraph(f'字段{i:02d}：{value}')
    stream=BytesIO();document.save(stream)
    response=client.post('/api/contracts/import',files={'file':('分页核验合同.docx',stream.getvalue())})
    assert response.status_code==200,response.text
    return response.json()['source_id']


def validation(client,count=32,policy="manual"):
    record,base=setup_template(client)
    source=upload_rows(client,['____']*count)
    changed=client.put(base,json={'name':'分页标准模板','group_id':record['group_id'],'source_id':source,'revision':1}).json()
    fields=[{'id':f'f{i}','name':f'字段{i:02d}','block_id':f'b{i}','start':5,'end':9,'type':'text','policy':policy,'required':True,'confirmed':True} for i in range(count)]
    saved=client.put(base+'/review',json={'revision':changed['revision'],'source_id':source,'fields':fields})
    assert saved.status_code==200,saved.text
    release=client.post(base+'/publish',json={'revision':saved.json()['revision']}).json()
    candidate=upload_rows(client,[f'内容{i:02d}' for i in range(count)])
    checked=client.post(base+'/validate',json={'release_id':release['release_id'],'source_id':candidate})
    assert checked.status_code==200,checked.text
    return checked.json(),base,release


def test_validation_saves_computed_result_without_human_approval():
    with TestClient(app) as client:
        record,_,_=validation(client,3)
        assert record['status']=='completed' and record['passed'] is False
        assert 'confirmation' not in record
        assert record['source_sha256'] and record['template_sha256']
        detail='/api/template-validations/'+record['id']
        assert client.get(detail).json()['report']==record['report']
        assert client.get('/api/template-validations?passed=false').json()['total']==1
        assert client.get('/api/template-validations?passed=true').json()['total']==0
        assert client.post(detail+'/confirm',json={}).status_code in (404,405)
        assert template_review.repo().get(record['id'])['revision']==record['revision']


def test_only_complete_rule_pass_returns_true(monkeypatch):
    with TestClient(app) as client:
        record,base,release=validation(client,2,policy='conditional')
        assert record['passed'] is True
        source=upload_rows(client,['内容00',''])
        different=client.post(base+'/validate',json={'release_id':release['release_id'],'source_id':source}).json()
        assert different['passed'] is False
        original=template_review.document_blocks
        def incomplete(source_id):
            data=original(source_id)
            data['warnings']=['存在未能校验的复杂对象']
            return data
        monkeypatch.setattr(template_review,'document_blocks',incomplete)
        unverified=client.post(base+'/validate',json={'release_id':release['release_id'],'source_id':record['source_id']}).json()
        assert unverified['passed'] is False
        assert unverified['report']['limitations']
        assert client.get('/api/template-validations/'+record['id']).json()['passed'] is True


def test_legacy_approval_does_not_override_calculated_outcome():
    with TestClient(app) as client:
        record,_,_=validation(client,1)
        template_review.repo().update(record['id'],{'status':'confirmed','passed':True,'confirmation':{'reviewer':'旧审核人','conclusion':'approved'}})
        detail=client.get('/api/template-validations/'+record['id']).json()
        assert detail['passed'] is False and detail['status']=='completed'
        assert 'confirmation' not in detail
        listing=client.get('/api/template-validations?passed=false').json()
        assert listing['total']==1 and listing['items'][0]['passed'] is False
        assert template_review.repo().get(record['id'])['confirmation']['reviewer']=='旧审核人'


def test_history_pagination_filters_and_lightweight_summaries():
    with TestClient(app) as client:
        record,_,_=validation(client,1)
        for i in range(11):
            template_review.repo().create('template_validation',{**{k:v for k,v in record.items() if k not in ('id','revision','created_at','updated_at')},'filename':f'历史合同{i}'})
        first=client.get('/api/template-validations?page_size=10').json()
        second=client.get('/api/template-validations?page_size=10&page=2').json()
        assert first['total']==12 and len(first['items'])==10 and len(second['items'])==2
        assert not set(r['id'] for r in first['items']) & set(r['id'] for r in second['items'])
        assert all('report' not in r and 'values' not in r for r in first['items'])
        assert client.get('/api/template-validations?q=历史合同10').json()['total']==1
        assert client.get('/api/template-validations?page=0').status_code==422


def test_browser_report_is_read_only_and_shows_paginated_failures():
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright,expect
    with TestClient(app) as client: record,_,_=validation(client)
    conclusion={'pass':'符合已配置规则','needs_changes':'需修改','needs_review':'需人工确认','incomplete':'检查不完整'}[record['report']['status']]
    with live_server() as address,sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1100})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(address+'/validation-records?validation='+record['id'])
        expect(page.get_by_role('heading',name=conclusion,exact=True)).to_be_visible()
        expect(page.locator('.report-table-wrap tbody tr')).to_have_count(10)
        page.get_by_role('button',name='下一页',exact=True).click()
        expect(page.locator('.report-table-wrap').get_by_text('字段10',exact=True)).to_be_visible()
        expect(page.get_by_role('navigation',name='报告分页')).to_contain_text('第 2 / 4 页')
        expect(page.get_by_role('button',name='确认审核',exact=False)).to_have_count(0)
        expect(page.get_by_label('审核人',exact=True)).to_have_count(0)
        page.screenshot(path='artifacts/prototypes/template-validation-read-only.png',full_page=True)
        page.reload()
        expect(page.get_by_role('heading',name=conclusion,exact=True)).to_be_visible()
        page.locator('.report-heading-actions').get_by_role('link',name='核验记录',exact=True).click()
        expect(page.get_by_role('heading',name='模板核验记录',exact=True)).to_be_visible()
        expect(page.locator('.template-records-table').get_by_text(conclusion,exact=True)).to_be_visible()
        page.get_by_label('核验结论',exact=True).select_option('true')
        expect(page.get_by_text('暂无匹配的核验记录',exact=True)).to_be_visible()
        page.get_by_label('核验结论',exact=True).select_option('all')
        page.locator('.template-records-table').get_by_role('link',name='查看报告',exact=True).click()
        expect(page.get_by_role('heading',name='模板核验报告',exact=True)).to_be_visible()
        page.locator('.portal-sidebar').get_by_role('link',name='审查记录',exact=True).click()
        expect(page.get_by_role('heading',name='审查记录',exact=True)).to_be_visible()
        expect(page.get_by_role('navigation',name='审查记录类型')).to_have_count(0)
        page.goto(address+'/records?tab=templates&validation='+record['id'])
        expect(page).to_have_url(address+'/validation-records?validation='+record['id'])
        assert not errors
        browser.close()
