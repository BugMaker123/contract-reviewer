"""Chinese evidence retrieval; always return unchanged source excerpts."""
import re

import jieba


_tokenizer = jieba.Tokenizer()
for _word in ('增值税', '违约金', '法定代表人', '知识产权', '不可抗力', '供方', '需方'):
    _tokenizer.add_word(_word)
_STOP_WORDS = {'的', '了', '和', '与', '或', '及', '在', '应', '应当', '合同', '约定', '条款'}


def search_terms(query):
    return list(dict.fromkeys(word.lower() for word in _tokenizer.cut(query, HMM=False)
                             if len(word.strip()) >= 2 and word not in _STOP_WORDS
                             and re.search(r'[\w\u4e00-\u9fff]', word)))


def search_excerpt(text, query):
    position = text.find(query)
    if position >= 0:
        start = max(0, position - 200)
        return {'start': start, 'text': text[start:position + 1000], 'match_type': 'exact'}
    terms = search_terms(query)
    if not terms:
        return None
    # Bound proximity: unrelated words elsewhere in a long contract are not a hit.
    for paragraph in re.finditer(r'[^\r\n]+', text):
        value = paragraph.group()
        lowered = value.lower()
        first = lowered.find(terms[0])
        while first >= 0:
            left, right = max(0, first - 500), min(len(value), first + 500)
            if all(term in lowered[left:right] for term in terms):
                start = paragraph.start() + left
                return {'start': start, 'text': text[start:paragraph.start() + right],
                        'match_type': 'segmented', 'terms': terms}
            first = lowered.find(terms[0], first + 1)
    return None


def revision_opcodes(original, revised):
    """Word-level edits with exact character offsets, including whitespace."""
    from difflib import SequenceMatcher

    before = list(_tokenizer.cut(original, HMM=False))
    after = list(_tokenizer.cut(revised, HMM=False))
    def offsets(tokens):
        result = [0]
        for token in tokens:
            result.append(result[-1] + len(token))
        return result
    left, right = offsets(before), offsets(after)
    for tag, a, b, c, d in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        original_part, revised_part = original[left[a]:left[b]], revised[right[c]:right[d]]
        # Numeric tokens need exact digit-level highlighting (30 -> 60 changes
        # only the first digit); Chinese legal terms remain whole-word edits.
        if tag == 'replace' and re.fullmatch(r'[0-9.,%+\-]+', original_part) and re.fullmatch(r'[0-9.,%+\-]+', revised_part):
            prefix=0
            while prefix<min(len(original_part),len(revised_part)) and original_part[prefix]==revised_part[prefix]:
                prefix+=1
            suffix=0
            while suffix<min(len(original_part),len(revised_part))-prefix and original_part[-1-suffix]==revised_part[-1-suffix]:
                suffix+=1
            if prefix:
                yield 'equal',left[a],left[a]+prefix,right[c],right[c]+prefix
            x,y=left[a]+prefix,left[b]-suffix
            u,v=right[c]+prefix,right[d]-suffix
            yield 'replace' if x<y and u<v else 'delete' if x<y else 'insert',x,y,u,v
            if suffix:
                yield 'equal',y,left[b],v,right[d]
        else:
            yield tag, left[a], left[b], right[c], right[d]
