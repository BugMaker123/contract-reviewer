import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from backend import graph, workspace_review
from backend.redaction import RedactionSession


TEXT = ('甲方（供方）：山东测试有限公司\n乙方：北京采购有限公司\n'
        '法定代表人：张三\n地址：山东省济南市历下区测试路12号\n'
        '电话：13800138000\n邮箱：alice@example.com\n'
        '银行账号：6222021234567890123\n身份证：110105199001011234\n'
        '统一社会信用代码：91370100MA12345678\n'
        '价款100000元，税率13%，2026年10月23日签署，30日内付款。')
SECRETS = ['山东测试有限公司', '北京采购有限公司', '张三', '山东省济南市历下区测试路12号',
           '13800138000', 'alice@example.com', '6222021234567890123', '110105199001011234', '91370100MA12345678']


def joined(messages):
    return '\n'.join(message.content for message in messages)


@pytest.mark.parametrize('ascii_only', [False, True])
def test_all_prompt_sources_are_redacted_without_mutating_input(ascii_only):
    original = [HumanMessage(content=json.dumps({'text': TEXT, 'references': [{'text': TEXT}],
                     'background': TEXT, 'prior_resolutions': [{'original_text': TEXT}]}, ensure_ascii=ascii_only))]
    before = deepcopy(original)
    session = RedactionSession()
    output = session.messages(original)
    payload = joined(output)
    for secret in SECRETS:
        assert secret not in payload
        assert json.dumps(secret, ensure_ascii=True)[1:-1] not in payload
    decoded = json.loads(output[-1].content)
    assert decoded['text'] == decoded['references'][0]['text'] == decoded['background']
    assert '100000元' in decoded['text'] and '13%' in decoded['text'] and '30日' in decoded['text']
    assert original == before
    assert session.restore(decoded)['text'] == TEXT


def test_blank_fields_are_not_replaced_or_merged_with_next_line():
    text = '甲方：\n乙方：____\n法定代表人：\n地址：\n银行账号：____\n30日内付款。'
    session = RedactionSession()
    assert session.messages([HumanMessage(content=text)])[-1].content == text
    assert not session.values


def test_repeated_values_and_request_isolation():
    a, b = RedactionSession(), RedactionSession()
    a.messages([HumanMessage(content=TEXT)])
    b.messages([HumanMessage(content=TEXT)])
    assert a.values['张三'] != b.values['张三']
    token = a.values['山东测试有限公司']
    assert a.redact_text('山东测试有限公司应向山东测试有限公司付款。').count(token) == 2


def test_restore_quoted_and_newline_values_as_json_values():
    session = RedactionSession()
    session._remember('地址', '测试路"甲号"\n第二层')
    token = next(iter(session.values.values()))
    result = session.result(json.loads(json.dumps({'evidence': token})))
    assert result['evidence'] == '测试路"甲号"\n第二层'


def test_unknown_tokens_fail_closed():
    with pytest.raises(ValueError, match='代号'):
        RedactionSession().result({'answer': '【隐私_姓名_forged_1】'})


def test_neighboring_payment_clause_remains_reviewable_and_anchor_restores():
    session = RedactionSession()
    session.messages([HumanMessage(content=TEXT)])
    token = session.values['山东测试有限公司']
    issue = {'issue_title': '付款期限过长', 'redline': {
        'original_text': token + '应于60日内付款。', 'suggested_text': token + '应于30日内付款。', 'change_type': 'replace'}}
    result = session.result({'issues': [issue]})['issues'][0]
    assert result['redline']['original_text'] == '山东测试有限公司应于60日内付款。'
    assert result['redline']['suggested_text'] == '山东测试有限公司应于30日内付款。'


@pytest.mark.parametrize('kind', ['replace', 'delete'])
def test_sensitive_fields_cannot_be_removed_by_redlines(kind):
    session = RedactionSession()
    session.messages([HumanMessage(content=TEXT)])
    token = session.values['张三']
    result = session.result({'issues': [{'issue_title': '调整条款', 'redline': {
        'original_text': '联系人：' + token, 'suggested_text': '联系人：李四', 'change_type': kind}}]})
    assert result['issues'][0]['redline'] is None


def test_sensitive_only_findings_are_skipped_but_real_blanks_survive():
    session = RedactionSession()
    session.messages([HumanMessage(content=TEXT)])
    token = session.values['张三']
    issues = [{'issue_title': '法定代表人姓名不完整', 'redline': None, 'evidence': '法定代表人：' + token},
              {'issue_title': '地址空白', 'redline': None, 'evidence': '地址：____'}]
    assert session.result({'issues': issues})['issues'] == [issues[1]]


def test_sensitive_value_verification_is_pending_but_payment_deadline_is_preserved():
    session = RedactionSession()
    session.messages([HumanMessage(content=TEXT)])
    token = session.values['山东测试有限公司']
    result = session.result({'findings': [
        {'text': '核实公司名称', 'status': 'pass', 'evidence': token},
        {'text': '付款期限不超过30日', 'status': 'pass', 'evidence': token + '30日内付款'}]})
    assert result['findings'][0]['status'] == 'needs_review'
    assert result['findings'][1]['status'] == 'pass'


def test_async_boundary_and_retries_never_send_raw_values(monkeypatch):
    class Client:
        calls = 0
        async def ainvoke(self, messages):
            self.calls += 1
            payload = joined(messages)
            assert all(secret not in payload for secret in SECRETS)
            if self.calls == 1:
                return SimpleNamespace(content='invalid JSON 张三')
            body = json.loads(messages[2].content)
            return SimpleNamespace(content=json.dumps({'answer': body['text']}, ensure_ascii=False))
    client = Client()
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: client)
    result = asyncio.run(workspace_review.model_json({'max_retries': 1}, json.dumps({'text': TEXT}, ensure_ascii=False)))
    assert result['answer'] == TEXT
    assert client.calls == 2


@pytest.mark.parametrize('streaming', [False, True])
def test_sync_provider_boundary_including_streaming_and_original_anchors(streaming):
    class Client:
        def invoke(self, messages):
            assert all(secret not in joined(messages) for secret in SECRETS)
            masked = json.loads(messages[-1].content)['text']
            issue = {'id': 'a', 'clause_title': '付款', 'severity': 'warning', 'category': '付款',
                     'issue_title': '付款期限过长', 'legal_basis': '合同约定', 'risk_analysis': '履约风险',
                     'negotiation_strategy': '调整期限', 'redline': {'original_text': masked,
                     'suggested_text': masked.replace('30日', '15日'), 'change_type': 'replace'}}
            return SimpleNamespace(content=json.dumps({'issues': [issue]}, ensure_ascii=False))
    class StreamingClient(Client):
        def stream(self, messages):
            content = self.invoke(messages).content
            for index in range(0, len(content), 7):
                yield SimpleNamespace(content=content[index:index + 7])
    client = StreamingClient() if streaming else Client()
    result = graph.invoke_review_with_retry(client, [HumanMessage(content=json.dumps({'text': TEXT}, ensure_ascii=False))], {'max_retries': 0})
    assert result['issues'][0]['redline']['original_text'] == TEXT
    assert '15日' in result['issues'][0]['redline']['suggested_text']


def test_batch_rewrite_rejects_modified_hidden_values(monkeypatch):
    class Client:
        async def ainvoke(self, messages):
            assert '张三' not in joined(messages)
            return SimpleNamespace(content=json.dumps({'revisions': [{'id': 'a', 'suggested_text': '联系人：李四'}]}))
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: Client())
    with pytest.raises(graph.ModelCallError):
        asyncio.run(workspace_review.model_json({'max_retries': 0, '_required_json_arrays': ['revisions'],
            '_revision_originals': {'a': '联系人：张三'}}, '联系人：张三'))


def test_party_token_order_cannot_be_swapped():
    session = RedactionSession()
    session.messages([HumanMessage(content=TEXT)])
    a, b = session.values['山东测试有限公司'], session.values['北京采购有限公司']
    result = session.result({'issues': [{'issue_title': '调整主体条款', 'redline': {
        'original_text': '甲方：' + a + '，乙方：' + b,
        'suggested_text': '甲方：' + b + '，乙方：' + a, 'change_type': 'replace'}}]})
    assert result['issues'][0]['redline'] is None


def test_api_keeps_original_document_and_only_sends_redacted_copies(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app
    calls = []
    class Client:
        def inspect(self, messages):
            payload = joined(messages)
            assert all(secret not in payload for secret in SECRETS)
            calls.append(payload)
        async def ainvoke(self, messages):
            self.inspect(messages)
            return SimpleNamespace(content=json.dumps({'status': 'pass', 'reason': '合同审查用途'}))
        def stream(self, messages):
            self.inspect(messages)
            yield SimpleNamespace(content='{"issues":[],"tax_settlement":{}}')
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: Client())
    with TestClient(app) as client:
        task = client.post('/api/tasks', json={'title': '采购协议', 'text': TEXT, 'mode': 'deep'}).json()
        response = client.post('/api/tasks/' + task['id'] + '/review/stream', json={})
        assert 'event: complete' in response.text
        saved = client.get('/api/tasks/' + task['id']).json()
        assert saved['text'] == TEXT
        assert saved['run']['input']['text'] == TEXT
        assert any(event['stage'] == 'redaction' for event in saved['run']['audit_trace'])
        assert '【隐私_' not in json.dumps(saved, ensure_ascii=False)
        assert len(calls) >= 2


def test_nontext_input_is_blocked_before_provider_call():
    session = RedactionSession()
    with pytest.raises(ValueError, match='非文本'):
        session.messages([HumanMessage(content=[{'type': 'image_url', 'image_url': {'url': 'https://example.invalid/private.png'}}])])


def test_id_only_requirement_results_are_guarded_using_request_metadata():
    session = RedactionSession()
    session.messages([HumanMessage(content=TEXT)])
    result = session.result({'findings': [{'id': 'r1', 'status': 'pass', 'evidence': session.values['张三']}]},
                            requirement_texts={'r1': '核验法定代表人姓名'})
    assert result['findings'][0]['status'] == 'needs_review'
