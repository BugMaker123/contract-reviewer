import pytest
import json
from types import SimpleNamespace
from fastapi.testclient import TestClient

from backend import graph, workspace_api
from backend.main import app


def test_deep_review_without_model_fails_instead_of_using_sample_rules(monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with pytest.raises(graph.ModelCallError, match='未连接模型'):
        graph.node_balance_review({'review_mode': 'deep', 'contract_text': '不同的合同'})


def test_authentication_failure_is_actionable_and_does_not_expose_key(monkeypatch):
    class Unauthorized(Exception):
        status_code = 401

    class Model:
        def invoke(self, messages):
            raise Unauthorized('private-api-key')

    monkeypatch.setattr(graph, 'get_llm_client', lambda config: Model())
    with pytest.raises(graph.ModelCallError, match='鉴权失败') as error:
        graph.node_balance_review({'review_mode': 'deep', 'contract_text': '真实合同'})
    assert 'private-api-key' not in str(error.value)


def test_summary_has_no_fixed_score_or_unrelated_template_advice():
    result = graph.node_synthesize_summary({'review_mode': 'quick', 'all_issues': [
        {'severity': 'warning', 'issue_title': '交付期限不明确', 'negotiation_strategy': '明确交付日期'}]})
    summary = result['overall_summary']
    assert summary['compliance_score'] is None
    assert summary['action_advice'] == ['明确交付日期']
    assert '交付期限' in summary['verdict']
    assert '增值税' not in summary['verdict']


def test_stream_reports_model_failure_and_does_not_store_completed_result(isolated_workspace, monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with TestClient(app) as client:
        task = client.post('/api/tasks', json={'title':'真实模型失败测试', 'text':'第一条 交付设备。', 'mode':'deep'}).json()
        response = client.post('/api/tasks/'+task['id']+'/review/stream', json={})
        assert 'event: error' in response.text and '未连接模型' in response.text
        assert 'event: complete' not in response.text
        saved = workspace_api.repo.get(task['id'])
        assert saved['status'] == 'failed' and not saved.get('active_run')


def test_review_parser_accepts_text_wrapper_and_optional_metadata():
    data = {'issues': [{'clause_title':'交付', 'severity':'warning', 'category':'交付验收',
                       'issue_title':'交付期限不明确', 'risk_analysis':'履约时间存在争议',
                       'negotiation_strategy':'明确期限', 'redline': {
                           'original_text':'交付设备。', 'suggested_text':'于【待确认日期】交付设备。'}}]}
    response = SimpleNamespace(content='审查如下：\n```json\n'+json.dumps(data)+'\n```')
    result = graph.parse_model_review(response)
    assert result['issues'][0]['id'] == 'issue_1'
    assert result['issues'][0]['redline']['suggested_text'] == '于【待确认日期】交付设备。'
    assert result['tax_settlement'] == {}


def test_review_parser_reports_specific_missing_fields():
    with pytest.raises(graph.ModelCallError, match='risk_analysis') as error:
        graph.parse_model_review(SimpleNamespace(content=json.dumps({'issues':[{}]})))
    assert graph.model_failure_reason(error.value) == str(error.value)


def test_review_parser_reports_truncation_and_invalid_json():
    with pytest.raises(graph.ModelCallError, match='截断'):
        graph.parse_model_review(SimpleNamespace(content='{}', response_metadata={'finish_reason':'length'}))
    with pytest.raises(graph.ModelCallError, match='不是完整的 JSON'):
        graph.parse_model_review(SimpleNamespace(content='仅有说明，没有结构化结果'))
