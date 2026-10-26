import asyncio
import re
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend import graph, knowledge, workspace_api, workspace_review
from backend.main import app
from backend.store import Repository


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with TestClient(app) as client:
        yield client


def add_document(client, text='采购制度：验收合格后支付货款。付款必须取得发票。', name='采购制度'):
    source = workspace_api.repo.create('source', {'name': name + '.txt', 'extension': '.txt', 'text': text})
    response = client.post('/api/knowledge/documents', json={'source_id': source['id'], 'name': name})
    assert response.status_code == 200, response.text
    return response.json()


def test_offsets_and_local_retrieval_are_source_grounded(client):
    text = '\n' + ('验收合格后支付货款。\n' * 180)
    document = add_document(client, text)
    data = client.get('/api/knowledge/documents/' + document['id']).json()
    assert len(data['chunks']) > 1
    assert ''.join(item['text'] for item in data['chunks']) == text
    for item in data['chunks']:
        assert text[item['start']:item['end']] == item['text']
    hits = client.get('/api/knowledge/search', params={'q': '验收', 'document_ids': document['id']}).json()['citations']
    assert hits and hits[0]['method'] == 'local-cooccurrence'
    assert all(item['digest'] == document['digest'] for item in hits)
    assert client.get('/api/knowledge/search', params={'q': '验收'}).json()['citations'] == []


def test_cross_document_graph_expands_to_nonlexical_evidence(client):
    first = add_document(client, '预付款由财务部审批。', '审批制度')
    second = add_document(client, '财务部必须审核票据。', '发票制度')
    repo = workspace_api.repo
    repo.update(first['id'], {'entities': [{'name': '预付款'}, {'name': '财务部'}], 'relations': [
        {'source': '预付款', 'target': '财务部', 'relation': '审批部门', 'chunk_id': 'c1', 'evidence': '预付款由财务部审批。'}]})
    repo.update(second['id'], {'entities': [{'name': '财务部'}, {'name': '票据'}], 'relations': [
        {'source': '财务部', 'target': '票据', 'relation': '审核', 'chunk_id': 'c1', 'evidence': '财务部必须审核票据。'}]})
    hits = knowledge.retrieve(repo, [first['id'], second['id']], '预付款')
    expanded = next(item for item in hits if item['document_id'] == second['id'])
    assert expanded['match'] == 'graph'
    assert expanded['paths'][0]['evidence'] == '财务部必须审核票据。'


def test_semantic_graph_rejects_fabricated_relationship_evidence():
    async def invalid(config, prompt):
        return {'entities': [{'name': '财务部', 'chunk_id': 'c1', 'evidence': '财务部审核票据。'},
                             {'name': '票据', 'chunk_id': 'c1', 'evidence': '财务部审核票据。'}],
                'relations': [{'source': '财务部', 'target': '票据', 'relation': '批准', 'chunk_id': 'c1', 'evidence': '财务部批准票据。'}]}
    with pytest.raises(ValueError, match='关系缺少有效原文依据'):
        asyncio.run(knowledge.semantic_graph(knowledge.chunks('财务部审核票据。'), {}, invalid))


def test_failed_index_preserves_old_graph_and_model_config_not_stored(client, monkeypatch):
    document = add_document(client)
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    async def invalid(*args):
        return {'entities': [{'name': '不存在', 'chunk_id': 'c1', 'evidence': '凭空引用'}], 'relations': []}
    monkeypatch.setattr(workspace_review, 'model_json', invalid)
    response = client.post('/api/knowledge/documents/' + document['id'] + '/index', json={
        'revision': document['revision'], 'model_config_data': {'api_key': 'secret-not-to-save'}})
    assert response.status_code == 422
    latest = client.get('/api/knowledge/documents/' + document['id'])
    assert latest.json()['revision'] == document['revision']
    assert latest.json()['method'] == 'local-cooccurrence'
    assert 'secret-not-to-save' not in latest.text


def test_semantic_index_and_model_conversation_keep_validated_quotes(client, monkeypatch):
    document = add_document(client, '财务部审核票据。')
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    calls = []
    async def model(config, prompt):
        calls.append(prompt)
        if '从资料提取' in prompt:
            return {'entities': [{'name': name, 'chunk_id': 'c1', 'evidence': '财务部审核票据。'} for name in ('财务部', '票据')],
                    'relations': [{'source': '财务部', 'target': '票据', 'relation': '审核', 'chunk_id': 'c1', 'evidence': '财务部审核票据。'}]}
        return {'answer': '财务部负责审核票据。', 'citations': [{'id': document['id'] + ':c1', 'quote': '财务部审核票据。'}]}
    monkeypatch.setattr(workspace_review, 'model_json', model)
    indexed = client.post('/api/knowledge/documents/' + document['id'] + '/index', json={'revision': 1})
    assert indexed.status_code == 200 and indexed.json()['method'] == 'model-entities-relations'
    session = client.post('/api/knowledge/sessions', json={}).json()
    response = client.post('/api/knowledge/sessions/' + session['id'] + '/messages', json={
        'revision': 1, 'question': '谁审核票据？', 'document_ids': [document['id']]})
    assert response.status_code == 200, response.text
    session = response.json()
    assert session['messages'][-1]['citations'][0]['quote'] == '财务部审核票据。'
    assert session['messages'][-1]['mode'] == 'model'
    response = client.post('/api/knowledge/sessions/' + session['id'] + '/messages', json={
        'revision': session['revision'], 'question': '那需要谁确认？', 'document_ids': [document['id']]})
    assert response.status_code == 200
    assert '谁审核票据' in calls[-1] and '财务部负责审核票据' in calls[-1]


def test_bad_citations_do_not_persist_a_failed_turn(client, monkeypatch):
    document = add_document(client)
    session = client.post('/api/knowledge/sessions', json={}).json()
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    async def bad(*args):
        return {'answer': '假的', 'citations': [{'id': document['id'] + ':c1', 'quote': '原文不存在的证据'}]}
    monkeypatch.setattr(workspace_review, 'model_json', bad)
    response = client.post('/api/knowledge/sessions/' + session['id'] + '/messages', json={
        'revision': 1, 'question': '付款', 'document_ids': [document['id']]})
    assert response.status_code == 422
    assert client.get('/api/knowledge/sessions/' + session['id']).json()['messages'] == []


def test_offline_chat_revision_conflicts_and_restart_persistence(client):
    document = add_document(client)
    session = client.post('/api/knowledge/sessions', json={}).json()
    body = {'revision': session['revision'], 'question': '付款需要什么？', 'document_ids': [document['id']]}
    response = client.post('/api/knowledge/sessions/' + session['id'] + '/messages', json=body)
    assert response.status_code == 200, response.text
    messages = response.json()['messages']
    assert messages[-1]['mode'] == 'extractive' and messages[-1]['citations']
    assert client.post('/api/knowledge/sessions/' + session['id'] + '/messages', json=body).status_code == 409
    reopened = Repository(workspace_api.repo.path)
    assert reopened.get(session['id'])['messages'] == messages


def test_review_requires_confirmation_and_keeps_immutable_evidence(client):
    document = add_document(client)
    session = client.post('/api/knowledge/sessions', json={}).json()
    session = client.post('/api/knowledge/sessions/' + session['id'] + '/messages', json={
        'revision': 1, 'question': '付款要求', 'document_ids': [document['id']]}).json()
    body = {'title': '采购合同', 'text': '甲方采购设备。乙方交付后付款，验收合格后支付货款。',
            'knowledge_document_ids': [document['id']], 'knowledge_session_id': session['id'],
            'knowledge_message_ids': [session['messages'][0]['id']]}
    assert client.post('/api/tasks', json=body).status_code == 422
    body['knowledge_context_confirmed'] = True
    response = client.post('/api/tasks', json=body)
    assert response.status_code == 200, response.text
    task = response.json()
    assert len(task['references']) == 2
    context = deepcopy(task['knowledge_context'])
    assert context['citations'] and context['messages'][0]['text'] == '付款要求'
    assert client.delete('/api/knowledge/documents/' + document['id'], params={'revision': 1}).status_code == 200
    body['revision'] = task['revision']
    saved = client.put('/api/tasks/' + task['id'], json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()['knowledge_context'] == context
    assert len(saved.json()['references']) == 2
    run = workspace_api.repo.start_run(task['id'])
    assert run['input']['knowledge_context'] == context


def test_deleted_or_unselected_documents_do_not_leak_into_search(client):
    first = add_document(client, '付款需发票。', '第一份制度')
    second = add_document(client, '付款需审批。', '第二份制度')
    hits = knowledge.retrieve(workspace_api.repo, [first['id']], '付款')
    assert hits and all(item['document_id'] == first['id'] for item in hits)
    assert client.delete('/api/knowledge/documents/' + second['id'], params={'revision': 9}).status_code == 409
    assert client.delete('/api/knowledge/documents/' + second['id'], params={'revision': 1}).status_code == 200
    assert client.get('/api/knowledge/search', params={'q': '付款', 'document_ids': second['id']}).status_code == 404


def test_retrieval_evidence_reaches_review_graph_and_saved_result(client, monkeypatch):
    document = add_document(client)
    task = client.post('/api/tasks', json={'title':'采购合同', 'text':'甲方采购设备，乙方交付后验收付款。',
                                         'knowledge_document_ids':[document['id']]}).json()
    observed = []
    class ReviewGraph:
        async def astream(self, state):
            observed.extend(state['reference_materials'])
            yield {'synthesize_summary': {'overall_summary': {'verdict':'测试核验'}, 'all_issues':[]}}
    monkeypatch.setattr(graph, 'review_graph_app', ReviewGraph())
    response = client.post('/api/tasks/' + task['id'] + '/review/stream', json={})
    assert response.status_code == 200
    saved = client.get('/api/tasks/' + task['id']).json()['run']
    assert saved['status'] == 'completed', saved
    assert '付款必须取得发票' in observed[0]['text']
    assert saved['result']['knowledge_context'] == task['knowledge_context']
    assert saved['input']['knowledge_context']['citations'][0]['document_id'] == document['id']


def test_browser_chat_upload_history_and_review_handoff(client, tmp_path):
    import socket
    import threading
    import time
    import uvicorn
    from playwright.sync_api import sync_playwright, expect

    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    base = f'http://127.0.0.1:{sock.getsockname()[1]}'
    server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.05)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=['--no-proxy-server'])
            page = browser.new_page(viewport={'width': 1600, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base + '/chat')
            expect(page.locator('.chat-welcome h1')).to_have_text('把合同问题，聊清楚。')
            expect(page.locator('.chat-error')).to_have_count(0)
            page.screenshot(path=str(tmp_path / 'chat-empty.png'))
            page.get_by_role('button', name='添加参考资料').click()
            page.locator('.chat-source-upload input').set_input_files({
                'name': '采购制度.txt', 'mimeType': 'text/plain',
                'buffer': '采购制度：付款必须在验收合格并收到发票后进行。财务部负责核对票据。'.encode()})
            expect(page.locator('.chat-source-row')).to_have_count(1)
            expect(page.locator('.chat-source-row input')).to_be_checked()
            page.get_by_role('button', name='关闭资料选择').click()
            page.get_by_role('textbox', name='输入问题').fill('采购制度中的付款条件是什么？')
            page.get_by_role('button', name='发送问题').click()
            expect(page.locator('.chat-message.assistant')).to_have_count(1)
            page.locator('.chat-references summary').click()
            expect(page.locator('.chat-reference')).to_contain_text('验收合格')
            page.get_by_role('textbox', name='输入问题').fill('还要核对哪些票据？')
            page.get_by_role('button', name='发送问题').click()
            expect(page.locator('.chat-message.assistant')).to_have_count(2)
            page.reload()
            page.locator('.chat-history nav button').first.click()
            expect(page.locator('.chat-message')).to_have_count(4)
            page.screenshot(path=str(tmp_path / 'chat-history.png'))
            page.locator('.chat-review').click()
            expect(page).to_have_url(re.compile('/reviews/new\\?knowledge_session='))
            page.locator('.knowledge-selection summary').click()
            expect(page.locator('.knowledge-messages label')).to_have_count(4)
            page.locator('.knowledge-docs input').first.check()
            page.locator('.knowledge-messages input').first.check()
            page.locator('.knowledge-confirm input').check()
            page.locator('.review-contract-panel input[type=file]').set_input_files({
                'name': '采购合同.txt', 'mimeType': 'text/plain',
                'buffer': '采购合同\n甲方向乙方采购设备。合同金额100元。乙方交付后，甲方验收并支付货款。'.encode()})
            page.get_by_role('button', name='进入工作台核对合同').click()
            page.wait_for_url('**/workbench?task=*')
            task_id = page.url.split('task=')[1]
            task = page.request.get(base + '/api/tasks/' + task_id).json()
            assert len(task['knowledge_context']['citations']) == 1
            assert len(task['knowledge_context']['messages']) == 1
            assert len(task['references']) == 2
            assert not errors, errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
