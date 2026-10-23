from backend.text_search import revision_opcodes


def test_word_diff_preserves_terms_and_exact_text():
    before = "甲方承担违约金。\n双方  确认。"
    after = "甲方承担赔偿金。\n双方  确认。"
    edits = list(revision_opcodes(before, after))
    assert "".join(before[a:b] for _, a, b, _, _ in edits) == before
    assert "".join(after[c:d] for _, _, _, c, d in edits) == after
    changed = [(before[a:b], after[c:d]) for tag, a, b, c, d in edits if tag != "equal"]
    assert changed == [("违约金", "赔偿金")]


def test_word_diff_insert_delete_and_empty():
    for before, after in [("", "新增条款"), ("原条款", ""), ("", ""), ("付款30日", "付款60日")]:
        edits = list(revision_opcodes(before, after))
        assert "".join(before[a:b] for _, a, b, _, _ in edits) == before
        assert "".join(after[c:d] for _, _, _, c, d in edits) == after
