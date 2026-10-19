from backend.text_search import search_excerpt, search_terms


def test_exact_source_offsets():
    text = '甲方付款。\n乙方提供增值税专用发票。'
    result = search_excerpt(text, '增值税专用发票')
    assert result['match_type'] == 'exact'
    assert text[result['start']:result['start'] + len(result['text'])] == result['text']


def test_segmented_retrieval_preserves_source():
    text = '甲方付款。\n乙方应开具增值税专用发票，适用税率为13%。'
    result = search_excerpt(text, '增值税 税率')
    assert result['match_type'] == 'segmented'
    assert '13%' in result['text']
    assert text[result['start']:result['start'] + len(result['text'])] == result['text']
    assert '增值税' in search_terms('增值税 税率')


def test_missing_or_distant_terms_are_not_evidence():
    assert search_excerpt('增值税专用发票。\n付款税率另议。', '增值税 税率') is None
    assert search_excerpt('甲方应付款。', '知识产权 违约金') is None
    assert search_excerpt('甲方应付款。', '的 和') is None
