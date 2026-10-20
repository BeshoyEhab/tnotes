from tnotes.textfmt import preserve_linebreaks


def test_single_newlines_become_markdown_hard_breaks():
    assert preserve_linebreaks("one\ntwo") == "one  \ntwo"


def test_blank_lines_remain_paragraph_breaks():
    assert preserve_linebreaks("one\n\ntwo") == "one\n\ntwo"


def test_fenced_code_is_left_alone():
    text = "before\n```\na\nb\n```\nafter"
    assert preserve_linebreaks(text) == "before  \n```\na\nb\n```\nafter"


def test_indented_code_is_left_alone():
    assert preserve_linebreaks("    a\n    b") == "    a\n    b"


def test_thematic_breaks_stay_markdown():
    assert preserve_linebreaks("one\n---\ntwo") == "one  \n---\ntwo"
