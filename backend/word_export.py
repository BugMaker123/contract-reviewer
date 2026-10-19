"""Word exports with real revision markup and comments; preserve uploaded DOCX layout when possible."""
from copy import deepcopy
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path
import os

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph


SOURCES = Path(os.environ.get('LEXIS_DATA_DIR') or Path(os.environ.get('LEXIS_DB_PATH') or Path(__file__).parent.parent / 'data' / 'lexis.db').parent) / 'sources'


def visible_paragraph_text(element):
    def read(node):
        if node.tag == qn('w:del'):
            return ''
        if node.tag == qn('w:t'):
            return node.text or ''
        if node.tag in (qn('w:br'), qn('w:cr')):
            return '\n'
        if node.tag == qn('w:tab'):
            return '\t'
        return ''.join(read(child) for child in node)
    return read(element)


def paragraphs(document):
    return [Paragraph(node, document) for node in document.element.body.iter(qn('w:p'))]


def add_revision(paragraph, old, new, counter, date):
    properties = deepcopy(paragraph.runs[0]._r.rPr) if paragraph.runs and paragraph.runs[0]._r.rPr is not None else None
    paragraph.clear()
    def append(text, kind=None):
        if not text:
            return
        if kind is None:
            run = paragraph.add_run(text)
            if properties is not None:
                run._r.insert(0, deepcopy(properties))
            return
        wrapper = OxmlElement('w:' + kind)
        wrapper.set(qn('w:id'), str(counter[0])); counter[0] += 1
        wrapper.set(qn('w:author'), 'LexisGraph')
        wrapper.set(qn('w:date'), date)
        node = OxmlElement('w:r')
        if properties is not None:
            node.append(deepcopy(properties))
        for index, line in enumerate(text.split('\n')):
            if index:
                node.append(OxmlElement('w:br'))
            value = OxmlElement('w:delText' if kind == 'del' else 'w:t')
            value.set(qn('xml:space'), 'preserve'); value.text = line; node.append(value)
        wrapper.append(node); paragraph._p.append(wrapper)
    for tag, a, b, c, d in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == 'equal':
            append(old[a:b])
        else:
            append(old[a:b], 'del'); append(new[c:d], 'ins')


def contract_document(run, final_text, repo, default_builder, tracked=False, base_document=None, base_layout=None):
    original = run['input']['text']
    source_id = run['input'].get('source_id')
    document = base_document
    layout = base_layout or 'reconstructed'
    if document is None and source_id:
        source = repo.get(source_id, 'source')
        if source['extension'] == '.docx' and source['text'] == original:
            document = Document(SOURCES / (source_id + '.docx'))
            layout = 'preserved'
    if document is None:
        document = default_builder(run['input']['title'], original)
        # Builder adds a title; it isn't part of the input being revised.
        source_paragraphs = paragraphs(document)[1:]
        if source_paragraphs and source_paragraphs[0].text == run['input']['title']:
            title_paragraph = paragraphs(document)[0]
            duplicate = source_paragraphs.pop(0)
            duplicate._p.getparent().remove(duplicate._p)
            source_paragraphs.insert(0, title_paragraph)
    else:
        source_paragraphs = paragraphs(document)
        if base_document is not None and layout == 'reconstructed':
            # The builder sometimes reuses the input's leading title rather than
            # adding a separate heading. Only skip a genuinely extra heading.
            if '\n'.join(visible_paragraph_text(p._p) for p in source_paragraphs) != original:
                source_paragraphs = source_paragraphs[1:]
    before = [visible_paragraph_text(p._p) for p in source_paragraphs]
    # Soft line breaks remain within paragraphs; applying revisions uses a character-to-paragraph mapping.
    if '\n'.join(before) != original:
        document = default_builder(run['input']['title'], original)
        source_paragraphs = paragraphs(document)[1:]
        before = [p.text for p in source_paragraphs]
        layout = 'reconstructed'
    after = final_text.split('\n')
    # Extracted text uses the same newline for soft breaks and paragraph boundaries.
    # When their count is unchanged, retain the source paragraph grouping (including tables).
    line_counts = [len(text.split('\n')) for text in before]
    if sum(line_counts) == len(after):
        grouped, offset = [], 0
        for count in line_counts:
            grouped.append('\n'.join(after[offset:offset + count]))
            offset += count
        after = grouped
    ids = [int(value) for value in document.element.xpath('//@w:id') if str(value).isdigit()]
    counter = [max(ids, default=0) + 1]
    stamp = run.get('completed_at', run['created_at'])
    # Reverse iteration keeps the original paragraph anchors stable while inserting new paragraphs.
    opcodes = [] if final_text == original else SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
    for tag, a, b, c, d in reversed(opcodes):
        if tag == 'equal':
            continue
        if tag == 'insert':
            for line in after[c:d]:
                if a < len(source_paragraphs):
                    p = source_paragraphs[a].insert_paragraph_before()
                else:
                    p = document.add_paragraph()
                if tracked:
                    add_revision(p, '', line, counter, stamp)
                else:
                    p.add_run(line)
        else:
            for index, p in enumerate(source_paragraphs[a:b]):
                # Adjacent revisions belong to their own paragraph/cell. Do not
                # combine the full replacement block into its first paragraph.
                if index >= d - c:
                    new = ''
                elif index == b - a - 1:
                    new = '\n'.join(after[c + index:d])
                else:
                    new = after[c + index]
                if tracked:
                    add_revision(p, before[a + index], new, counter, stamp)
                else:
                    properties = deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
                    p.clear(); r = p.add_run(new)
                    if properties is not None:
                        r._r.insert(0, properties)
    if tracked:
        setting = OxmlElement('w:trackRevisions')
        document.settings.element.append(setting)
    # Native Word comments remain anchored to the relevant current paragraph when it can be matched.
    for issue in ([] if base_document is not None else run['result']['issues']):
        note = run.get('comments', {}).get(issue['id'])
        if not note:
            continue
        evidence = issue.get('evidence') or (issue.get('redline') or {}).get('suggested_text') or (issue.get('redline') or {}).get('original_text')
        targets = [p for p in paragraphs(document) if evidence and (visible_paragraph_text(p._p) in evidence) and visible_paragraph_text(p._p).strip()]
        if not targets:
            targets = [p for p in paragraphs(document) if p.text == run['input']['title']]
        if targets:
            anchor = targets[0].runs[0] if targets[0].runs else targets[0].add_run('')
            document.add_comment(anchor, text=issue['issue_title'] + '\n' + note, author='内部复核', initials='LG')
    return document, layout


def edit_document_text(document, original, updated):
    """Apply text edits without clearing runs, paragraph properties or table structure."""
    items = paragraphs(document)
    before = [visible_paragraph_text(p._p) for p in items]
    if '\n'.join(before) != original:
        raise ValueError('文档正文与当前编辑稿不一致，请重新打开文档')
    lines = updated.split('\n')
    after, offset = [], 0
    for old in before:
        count = len(old.split('\n'))
        after.append('\n'.join(lines[offset:offset + count]))
        offset += count
    # Structural changes across tables cannot safely be inferred from plain text.
    if offset != len(lines):
        raise ValueError('请在原排版中修改段落内容，暂不支持增删段落')
    for paragraph, old, new in zip(items, before, after):
        if old == new:
            continue
        nodes = list(paragraph._p.iter(qn('w:t')))
        if ''.join(node.text or '' for node in nodes) != old:
            raise ValueError('该段落包含修订或特殊换行，暂不支持直接编辑，请先在 Word 中处理')
        offsets, start = [], 0
        for node in nodes:
            offsets.append((start, start + len(node.text or ''), node))
            start += len(node.text or '')
        if not nodes:
            paragraph.add_run(new)
            continue
        for tag, a, b, c, d in reversed(SequenceMatcher(None, old, new, autojunk=False).get_opcodes()):
            if tag == 'equal':
                continue
            anchor = next((i for i, (left, right, node) in enumerate(offsets) if left <= a < right), len(offsets)-1)
            for i in range(len(offsets)-1, -1, -1):
                left, right, node = offsets[i]
                text = node.text or ''
                lo, hi = max(a, left)-left, min(b, right)-left
                if hi > lo:
                    text = text[:lo] + text[hi:]
                if i == anchor:
                    pos = a-left
                    text = text[:pos] + new[c:d] + text[pos:]
                node.text = text
                node.set(qn('xml:space'), 'preserve')
    return document
