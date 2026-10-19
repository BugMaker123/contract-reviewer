import pytest
from copy import deepcopy

from backend import workspace_api, workspace_review
from test_tracked_revisions import revision_client, seed_review

from backend.rewrite_policy import adds_signing_reminder, REWRITE_WARNING
from backend.stance_policy import guard_generated_issues


REMINDER = '双方应在签署时填写完整本协议首部所列主体信息及签署页信息，并相互核验对方营业执照、从事本协议项下业务所需的资质及授权代表授权文件。'
ORIGINAL = '年度采购协议\n甲方（供方）：\n法定代表人：\n地址：\n乙方（需方）：\n法定代表人：\n地址：\n\n双方就采购事宜签署本协议。'


def test_screenshot_reminder_is_not_contract_rewrite():
    suggested = ORIGINAL.replace('\n\n', '\n\n' + REMINDER + '\n\n')
    assert adds_signing_reminder(ORIGINAL, suggested)
    issue = {'id': 'issue_1', 'issue_title': '主体信息空白', 'risk_analysis': '签署前需补全',
             'redline': {'original_text': ORIGINAL, 'suggested_text': suggested}}
    guarded = guard_generated_issues([issue], ORIGINAL)
    assert len(guarded) == 1
    assert guarded[0]['risk_analysis'] == issue['risk_analysis']
    assert guarded[0]['redline'] is None
    assert guarded[0]['rewrite_warning'] == REWRITE_WARNING


@pytest.mark.parametrize('before,after', [
    (REMINDER, REMINDER + '\n付款期限为30日。'),
    ('甲方提供资质证明。', '甲方应在交付前提供有效药品经营许可证，资质失效时乙方有权解除合同。'),
    ('甲方：\n乙方：', '甲方：某某公司\n乙方：另一公司'),
])
def test_existing_text_and_substantive_obligations_are_preserved(before, after):
    assert not adds_signing_reminder(before, after)


def test_previous_generated_reminder_cannot_be_accepted(revision_client):
    _, run = seed_review(revision_client)
    result = deepcopy(run['result'])
    issue = result['issues'][0]
    original = issue['redline']['original_text']
    issue['redline']['suggested_text'] = original + '\n' + REMINDER
    run = workspace_api.repo.update(run['id'], {'result': result})
    response = revision_client.put('/api/runs/' + run['id'] + '/handling',
                                  json={'revision': run['revision'], 'applied': [issue['id']]})
    assert response.status_code == 409
    assert REWRITE_WARNING in response.json()['detail']
    assert workspace_api.repo.get(run['id'])['applied'] == []


def test_regenerated_reminder_does_not_overwrite_previous_suggestion(revision_client, monkeypatch):
    _, run = seed_review(revision_client)
    issue = run['result']['issues'][0]
    async def generate(config, prompt):
        return {'suggested_text': issue['redline']['original_text'] + '\n' + REMINDER,
                'explanation': '补充签署提醒'}
    monkeypatch.setattr(workspace_review, 'model_json', generate)
    response = revision_client.post('/api/runs/' + run['id'] + '/issues/' + issue['id'] + '/regenerate',
                                   json={'revision': run['revision']})
    assert response.status_code == 422
    assert workspace_api.repo.get(run['id'])['result'] == run['result']
