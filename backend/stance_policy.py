"""A review perspective is not evidence of the parties' transaction identities."""
import re
from .rewrite_policy import adds_signing_reminder, REWRITE_WARNING

STANCE_INSTRUCTIONS = (
    '审查立场仅表示优先保护哪一方利益，不是合同事实，也不是改写甲乙方身份的指令。'
    '甲方不固定等于买方，乙方不固定等于卖方或服务方；供需、采购、供货、收付款、开票身份必须根据合同正文确定。'
    '旧版立场选项中括号内的买方/卖方/服务方说明不构成交易事实。'
    '禁止仅因正文身份与审查立场选项描述不同而认定合同有误、角色冲突或交换甲乙方、供需方。'
    '正文自身存在相互矛盾的身份或义务约定时，须逐字引用相互矛盾的两处正文，并提示人工核对，不得根据立场自动纠正主体身份。'
)
_DECLARATION = re.compile(r'([甲乙丙丁]方)\s*[（(]\s*([^）)\n]{1,24})[）)]')
_FLOW = re.compile(r'([甲乙丙丁]方)\s*向\s*([甲乙丙丁]方)\s*(采购|购买|供货|供应|出售)')
_BUY = {'需方', '买方', '采购方', '购买方'}
_SELL = {'供方', '卖方', '供应方', '供货方', '供应商'}


def perspective(role):
    match = re.match(r'\s*([甲乙丙丁]方)', role or '')
    return match.group(1) if match else role or '中立审慎'


def model_input(snapshot):
    return {**snapshot, 'role': perspective(snapshot.get('role'))}


def identities(text):
    values = {}
    for party, label in _DECLARATION.findall(text):
        label = re.sub(r'\s+', '', label)
        category = 'buyer' if label in _BUY else 'seller' if label in _SELL else 'provider' if label in {'服务方', '开发方', '受托方'} else None
        if category:
            values.setdefault(party, set()).add(category)
    return values


def internal_identity_conflict(text):
    facts = identities(text)
    if any(len(labels) > 1 for labels in facts.values()):
        return True
    for actor, target, verb in _FLOW.findall(text):
        if verb in ('采购', '购买') and ('seller' in facts.get(actor, set()) or 'buyer' in facts.get(target, set())):
            return True
        if verb in ('供货', '供应', '出售') and ('buyer' in facts.get(actor, set()) or 'seller' in facts.get(target, set())):
            return True
    return False


def changes_identity(original, suggested):
    before, after = identities(original), identities(suggested)
    if any(after.get(party) and after[party] != labels for party, labels in before.items()):
        return True
    original_flows = set(_FLOW.findall(original))
    return any((target, actor, verb) in original_flows for actor, target, verb in _FLOW.findall(suggested))


def stance_as_fact(issue, text):
    claim = issue.get('issue_title', '') + ' ' + issue.get('risk_analysis', '')
    return (not internal_identity_conflict(text)
            and bool(re.search(r'(?:审查|审核|所选|选定|选择|设置).{0,8}立场', claim))
            and any(word in claim for word in ('冲突', '不符', '不一致', '不匹配'))
            and any(word in claim for word in ('供方', '需方', '买方', '卖方', '供应商', '身份', '角色', '服务方'))
            and any(word in claim for word in ('身份', '角色', '首部', '前言', '标注', '写成', '定义', '称为')))


def guard_generated_issues(issues, text):
    kept = []
    for issue in issues:
        if stance_as_fact(issue, text):
            continue
        redline = issue.get('redline') or {}
        if adds_signing_reminder(redline.get('original_text', ''), redline.get('suggested_text', '')):
            issue = {**issue, 'redline': None, 'rewrite_warning': REWRITE_WARNING}
            redline = {}
        if changes_identity(redline.get('original_text', ''), redline.get('suggested_text', '')):
            issue = {**issue, 'redline': None,
                     'rewrite_warning': '自动修订改变了合同主体的供需身份或交易方向，已停止应用；请依据正文人工核对。'}
        kept.append(issue)
    return kept
