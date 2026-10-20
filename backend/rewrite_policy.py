"""Keep signing checklists out of generated contractual obligations."""
from difflib import SequenceMatcher
import re


REWRITE_INSTRUCTIONS = (
    '主体名称、法定代表人、地址或签署信息为空时，只在审查意见中提示补全和核验，保留正文空白。'
    '不得新增“双方应在签署时填写完整主体信息、核验营业执照及授权文件”等签署操作提醒来代替补全信息。'
    '此类提醒不属于可直接替换的合同条款；仅有此类问题时不要生成修订正文。'
)
REWRITE_WARNING = '签署信息补全或证照核验提醒应保留在审查意见中，已停止将其写入修订正文。'


def adds_signing_reminder(original, suggested):
    # Inspect only newly introduced text, never reject an existing source clause.
    for tag, _, _, start, end in SequenceMatcher(None, original, suggested, autojunk=False).get_opcodes():
        if tag not in ('insert', 'replace'):
            continue
        added = suggested[start:end]
        if (re.search(r'(?:填写|补全|补齐|补充|完善).{0,20}(?:主体信息|签署信息|签署页|法定代表人|联系地址)', added)
                or re.search(r'(?:签署前|签署时|签约前).{0,60}(?:核验|核对|查验).{0,30}(?:营业执照|授权文件|授权委托书|资质)', added)):
            return True
    return False
