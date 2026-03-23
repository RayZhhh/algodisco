from algodisco.toolkit.program_parser import CodeParser


def test_parse_preserves_python_docstring():
    code = 'def f():\n    """hello"""\n    return 1\n'

    parser = CodeParser("python")
    program = parser.parse(code, check_syntax_validity=False)

    assert program.functions[0].docstring == "hello"
    assert str(program) == code


def test_parse_preserves_raw_string_docstring():
    code = 'def f():\n    r"""hello"""\n    return 1\n'

    parser = CodeParser("python")
    program = parser.parse(code, check_syntax_validity=False)

    assert program.functions[0].docstring == "hello"
    assert str(program) == code


def test_parse_preserves_docstring_ending_with_quote():
    code = 'def f():\n    """ends with quote \\""""\n    return 1\n'

    parser = CodeParser("python")
    program = parser.parse(code, check_syntax_validity=False)

    assert program.functions[0].docstring == 'ends with quote "'
    assert str(program) == code
