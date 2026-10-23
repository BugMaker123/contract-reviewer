"""Local, request-scoped redaction at the model boundary. Never changes documents."""
from collections import Counter
from copy import deepcopy
import json
import re
from uuid import uuid4

from langchain_core.messages import SystemMessage

INSTRUCTIONS = (
    '【隐私_...】是系统替换的敏感字段值，表示该字段已填写，不是空白。'
    '跳过对这些值本身的真实性、格式、完整性和有效性的审查；不得猜测、补全、还原，'
    '不得因代号报告名称、姓名、地址、账号等信息缺失。'
    '继续审查周边付款、责任、期限等条款。引用时逐字保留代号；修订必须保留'
    '原条款中全部代号及出现次数，不得新增、删除、替换或交换主体代号。'
    '若核验依赖隐藏值，返回 needs_review 并说明敏感字段未参与审查。'
)
_LABELS = (
    ('身份证', r'身份证(?:号码|号)?', r'[0-9Xx -]{15,24}'),
    ('账户', r'(?:银行账号|银行账户|收款账号|收款账户|开户账号|开户账户|账号|帐号|卡号)', r'[0-9 -]{8,35}'),
    ('证件', r'(?:统一社会信用代码|纳税人识别号|税号)', r'[A-Za-z0-9]{15,20}'),
    ('姓名', r'(?:法定代表人|法人代表|授权代表|委托代理人|联系人|收款人|户名|姓名)', r'[\u4e00-\u9fff·]{2,20}'),
    ('地址', r'(?:(?:联系|通讯|通信|注册|办公|收货|送货|家庭|开户行)?地址|住所)', r'[^\r\n"\\,，;；。<>]{3,120}'),
    ('企业', r'(?:甲方|乙方|丙方|丁方|公司名称|企业名称|开户名称)(?:[（(][^）)\r\n]{1,20}[）)])?', r'[^\r\n"\\,，;；。<>]{2,100}'),
)
_FIELDS = [(kind, re.compile(label + r'\s*[:：][ \t]*(' + value + r')')) for kind, label, value in _LABELS]
_GLOBAL = [
    ('邮箱', re.compile(r'(?<![\w.+-])[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+')),
    ('电话', re.compile(r'(?<!\d)(?:\+?86[- ]?)?1[3-9]\d(?:[- ]?\d){8}(?!\d)')),
    ('电话', re.compile(r'(?<!\d)0\d{2,3}[- ]\d{7,8}(?!\d)')),
    ('身份证', re.compile(r'(?<![\dA-Za-z])\d{6}(?:19|20)\d{2}[01]\d[0-3]\d\d{3}[\dXx](?![\dA-Za-z])')),
    ('企业', re.compile(r'[\u4e00-\u9fffA-Za-z0-9（）()·]{2,60}?(?:有限责任公司|股份有限公司|有限公司|合伙企业)')),
]
_BLANK = re.compile(r'^(?:[_＿\s—-]+|待填写|待补充|待确认|未填写|无|不适用)$')
_KIND_LABELS = {'企业': ('主体名称', '公司名称', '企业名称', '方名称'), '姓名': ('姓名', '代表人', '联系人'),
                '地址': ('地址', '住所'), '账户': ('账号', '账户', '帐号'),
                '电话': ('电话', '手机'), '邮箱': ('邮箱', '邮件'),
                '身份证': ('身份证',), '证件': ('税号', '信用代码', '识别号')}


class RedactionSession:
    def __init__(self):
        self.namespace = uuid4().hex[:12]
        self.values = {}  # Raw value -> token. Only in memory, never logged/persisted.
        self.kinds = {}
        self.token_pattern = re.compile(r'【隐私_[^】]+】')

    def _remember(self, kind, value):
        if value and not _BLANK.fullmatch(value) and '【' not in value and value not in self.values:
            self.values[value] = f'【隐私_{kind}_{self.namespace}_{len(self.values) + 1}】'
            self.kinds[value] = kind

    def discover(self, text):
        for kind, pattern in _FIELDS:
            for match in pattern.finditer(text):
                value = re.split(r'\s+(?=\S{1,12}[:：])', match.group(1).strip())[0].strip()
                if kind in ('账户', '身份证') and not 8 <= len(re.sub(r'\D', '', value)) <= 22:
                    continue
                self._remember(kind, value)
        for kind, pattern in _GLOBAL:
            for match in pattern.finditer(text):
                self._remember(kind, match.group())

    def redact_text(self, text):
        if not self.values:
            return text
        pattern = re.compile(self.token_pattern.pattern + '|' + '|'.join(re.escape(v) for v in sorted(self.values, key=len, reverse=True)))
        return pattern.sub(lambda m: self.values.get(m.group(), m.group()), text)

    def _content(self, text):
        # Redact decoded JSON string values, rather than interpolating into JSON.
        pieces, cursor = [], 0
        for match in re.finditer(r'"(?:[^"\\]|\\.)*"', text):
            pieces.append(self.redact_text(text[cursor:match.start()]))
            try:
                decoded = json.loads(match.group())
                redacted = self.redact_text(decoded)
                pieces.append(match.group() if decoded == redacted else json.dumps(redacted, ensure_ascii=False))
            except ValueError:
                pieces.append(self.redact_text(match.group()))
            cursor = match.end()
        pieces.append(self.redact_text(text[cursor:]))
        return ''.join(pieces)

    def messages(self, messages):
        messages = list(messages)
        texts = []
        for message in messages:
            if not isinstance(message.content, str):
                raise ValueError('脱敏仅支持文本模型输入，已阻止发送非文本内容')
            texts.append(message.content)
            # Decode JSON string literals so unicode/newline escaping cannot bypass detection.
            for match in re.finditer(r'"(?:[^"\\]|\\.)*"', message.content):
                try:
                    texts.append(json.loads(match.group()))
                except ValueError:
                    pass
        for text in texts:
            self.discover(text)
        result = []
        for message in messages:
            content = self._content(message.content)
            result.append(message.model_copy(update={'content': content}))
        if self.values:
            result.insert(0, SystemMessage(content=INSTRUCTIONS))
        return result

    def tokens(self, text):
        # Order matters too: exchanging two parties must not pass integrity checks.
        return tuple(self.token_pattern.findall(text))

    def counts(self):
        return dict(Counter(self.kinds.values()))

    def concerns_hidden_value(self, text):
        return any(word in text for kind in set(self.kinds.values()) for word in _KIND_LABELS[kind])

    def restore(self, value):
        inverse = {token: raw for raw, token in self.values.items()}
        if isinstance(value, str):
            if set(self.token_pattern.findall(value)) - inverse.keys():
                raise ValueError('模型改变了脱敏代号，结果未保存')
            return self.token_pattern.sub(lambda m: inverse[m.group()], value)
        if isinstance(value, list):
            return [self.restore(item) for item in value]
        if isinstance(value, dict):
            return {key: self.restore(item) for key, item in value.items()}
        return value

    def result(self, value, originals=None, selected_original=None, requirement_texts=None):
        value = deepcopy(value)

        def visit(item):
            if isinstance(item, list):
                for child in item:
                    visit(child)
            elif isinstance(item, dict):
                redline = item.get('redline')
                if isinstance(redline, dict):
                    before, after = redline.get('original_text', ''), redline.get('suggested_text', '')
                    if (self.tokens(before) != self.tokens(after)
                            or (redline.get('change_type') == 'delete' and self.tokens(before))):
                        item['redline'] = None
                        item['rewrite_warning'] = '修订改变了隐藏的敏感字段，已停止自动应用，请人工核对。'
                if 'suggested_text' in item and not isinstance(redline, dict):
                    original = (originals or {}).get(item.get('id'), selected_original)
                    if original is not None and self.tokens(self.redact_text(original)) != self.tokens(item['suggested_text']):
                        raise ValueError('修订改变了隐藏的敏感字段')
                evidence = item.get('evidence', '')
                requirement = item.get('text', item.get('requirement', (requirement_texts or {}).get(item.get('id'), '')))
                if ((self.tokens(evidence) or not evidence) and item.get('status') in ('pass', 'fail')
                        and self.concerns_hidden_value(requirement)):
                    item.update(status='needs_review', explanation='证据涉及隐藏的敏感字段，相关值未参与核验，请人工确认。')
                for child in item.values():
                    visit(child)

        if isinstance(value, dict) and isinstance(value.get('issues'), list):
            def hidden_only(issue):
                claim = issue.get('issue_title', '')
                anchor = (issue.get('redline') or {}).get('original_text', '') or issue.get('evidence', '')
                return (any(word in claim for word in ('缺失', '空白', '不完整', '格式', '未填写', '未提供', '真实性', '有效性'))
                        and self.concerns_hidden_value(claim)
                        and bool(self.tokens(anchor)))
            value['issues'] = [issue for issue in value['issues'] if not hidden_only(issue)]
        visit(value)
        return self.restore(value)
