import numpy as np
import pytest

from pandas import (
    DataFrame,
    IndexSlice,
    MultiIndex,
    NaT,
    Timestamp,
    option_context,
)

pytest.importorskip("jinja2")
from pandas.io.formats.style import Styler
from pandas.io.formats.style_render import _str_escape


@pytest.fixture
def df():
    return DataFrame(
        data=[[0, -0.609], [1, -1.228]],
        columns=["A", "B"],
        index=["x", "y"],
    )


@pytest.fixture
def styler(df):
    return Styler(df, uuid_len=0)


def test_display_format(styler):
    ctx = styler.format("{:0.1f}")._translate(True, True)
    assert all(["display_value" in c for c in row] for row in ctx["body"])
    assert all([len(c["display_value"]) <= 3 for c in row[1:]] for row in ctx["body"])
    assert len(ctx["body"][0][1]["display_value"].lstrip("-")) <= 3


def test_format_dict(styler):
    ctx = styler.format({"A": "{:0.1f}", "B": "{0:.2%}"})._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "0.0"
    assert ctx["body"][0][2]["display_value"] == "-60.90%"


def test_format_string(styler):
    ctx = styler.format("{:.2f}")._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "0.00"
    assert ctx["body"][0][2]["display_value"] == "-0.61"
    assert ctx["body"][1][1]["display_value"] == "1.00"
    assert ctx["body"][1][2]["display_value"] == "-1.23"


def test_format_callable(styler):
    ctx = styler.format(lambda v: "neg" if v < 0 else "pos")._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "pos"
    assert ctx["body"][0][2]["display_value"] == "neg"
    assert ctx["body"][1][1]["display_value"] == "pos"
    assert ctx["body"][1][2]["display_value"] == "neg"


def test_format_with_na_rep():
    # GH 21527 28358
    df = DataFrame([[None, None], [1.1, 1.2]], columns=["A", "B"])

    ctx = df.style.format(None, na_rep="-")._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "-"
    assert ctx["body"][0][2]["display_value"] == "-"

    ctx = df.style.format("{:.2%}", na_rep="-")._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "-"
    assert ctx["body"][0][2]["display_value"] == "-"
    assert ctx["body"][1][1]["display_value"] == "110.00%"
    assert ctx["body"][1][2]["display_value"] == "120.00%"

    ctx = df.style.format("{:.2%}", na_rep="-", subset=["B"])._translate(True, True)
    assert ctx["body"][0][2]["display_value"] == "-"
    assert ctx["body"][1][2]["display_value"] == "120.00%"


def test_format_non_numeric_na():
    # GH 21527 28358
    df = DataFrame(
        {
            "object": [None, np.nan, "foo"],
            "datetime": [None, NaT, Timestamp("20120101")],
        }
    )
    ctx = df.style.format(None, na_rep="-")._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "-"
    assert ctx["body"][0][2]["display_value"] == "-"
    assert ctx["body"][1][1]["display_value"] == "-"
    assert ctx["body"][1][2]["display_value"] == "-"


def test_format_clear(styler):
    assert (0, 0) not in styler._display_funcs  # using default
    styler.format("{:.2f")
    assert (0, 0) in styler._display_funcs  # formatter is specified
    styler.format()
    assert (0, 0) not in styler._display_funcs  # formatter cleared to default


@pytest.mark.parametrize(
    "escape, exp",
    [
        ("html", "&lt;&gt;&amp;&#34;%$#_{}~^\\~ ^ \\ "),
        (
            "latex",
            '<>\\&"\\%\\$\\#\\_\\{\\}\\textasciitilde \\textasciicircum '
            "\\textbackslash \\textasciitilde \\space \\textasciicircum \\space "
            "\\textbackslash \\space ",
        ),
    ],
)
def test_format_escape_html(escape, exp):
    chars = '<>&"%$#_{}~^\\~ ^ \\ '
    df = DataFrame([[chars]])

    s = Styler(df, uuid_len=0).format("&{0}&", escape=None)
    expected = f'<td id="T__row0_col0" class="data row0 col0" >&{chars}&</td>'
    assert expected in s.to_html()

    # only the value should be escaped before passing to the formatter
    s = Styler(df, uuid_len=0).format("&{0}&", escape=escape)
    expected = f'<td id="T__row0_col0" class="data row0 col0" >&{exp}&</td>'
    assert expected in s.to_html()


def test_format_escape_na_rep():
    # tests the na_rep is not escaped
    df = DataFrame([['<>&"', None]])
    s = Styler(df, uuid_len=0).format("X&{0}>X", escape="html", na_rep="&")
    ex = '<td id="T__row0_col0" class="data row0 col0" >X&&lt;&gt;&amp;&#34;>X</td>'
    expected2 = '<td id="T__row0_col1" class="data row0 col1" >&</td>'
    assert ex in s.to_html()
    assert expected2 in s.to_html()


def test_format_escape_floats(styler):
    # test given formatter for number format is not impacted by escape
    s = styler.format("{:.1f}", escape="html")
    for expected in [">0.0<", ">1.0<", ">-1.2<", ">-0.6<"]:
        assert expected in s.to_html()
    # tests precision of floats is not impacted by escape
    s = styler.format(precision=1, escape="html")
    for expected in [">0<", ">1<", ">-1.2<", ">-0.6<"]:
        assert expected in s.to_html()


@pytest.mark.parametrize("formatter", [5, True, [2.0]])
def test_format_raises(styler, formatter):
    with pytest.raises(TypeError, match="expected str or callable"):
        styler.format(formatter)


def test_format_with_precision():
    # Issue #13257
    df = DataFrame(data=[[1.0, 2.0090], [3.2121, 4.566]], columns=["a", "b"])
    s = Styler(df)

    ctx = s.format(precision=1)._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "1.0"
    assert ctx["body"][0][2]["display_value"] == "2.0"
    assert ctx["body"][1][1]["display_value"] == "3.2"
    assert ctx["body"][1][2]["display_value"] == "4.6"

    ctx = s.format(precision=2)._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "1.00"
    assert ctx["body"][0][2]["display_value"] == "2.01"
    assert ctx["body"][1][1]["display_value"] == "3.21"
    assert ctx["body"][1][2]["display_value"] == "4.57"

    ctx = s.format(precision=3)._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == "1.000"
    assert ctx["body"][0][2]["display_value"] == "2.009"
    assert ctx["body"][1][1]["display_value"] == "3.212"
    assert ctx["body"][1][2]["display_value"] == "4.566"


def test_format_subset():
    df = DataFrame([[0.1234, 0.1234], [1.1234, 1.1234]], columns=["a", "b"])
    ctx = df.style.format(
        {"a": "{:0.1f}", "b": "{0:.2%}"}, subset=IndexSlice[0, :]
    )._translate(True, True)
    expected = "0.1"
    raw_11 = "1.123400"
    assert ctx["body"][0][1]["display_value"] == expected
    assert ctx["body"][1][1]["display_value"] == raw_11
    assert ctx["body"][0][2]["display_value"] == "12.34%"

    ctx = df.style.format("{:0.1f}", subset=IndexSlice[0, :])._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == expected
    assert ctx["body"][1][1]["display_value"] == raw_11

    ctx = df.style.format("{:0.1f}", subset=IndexSlice["a"])._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == expected
    assert ctx["body"][0][2]["display_value"] == "0.123400"

    ctx = df.style.format("{:0.1f}", subset=IndexSlice[0, "a"])._translate(True, True)
    assert ctx["body"][0][1]["display_value"] == expected
    assert ctx["body"][1][1]["display_value"] == raw_11

    ctx = df.style.format("{:0.1f}", subset=IndexSlice[[0, 1], ["a"]])._translate(
        True, True
    )
    assert ctx["body"][0][1]["display_value"] == expected
    assert ctx["body"][1][1]["display_value"] == "1.1"
    assert ctx["body"][0][2]["display_value"] == "0.123400"
    assert ctx["body"][1][2]["display_value"] == raw_11


@pytest.mark.parametrize("formatter", [None, "{:,.1f}"])
@pytest.mark.parametrize("decimal", [".", "*"])
@pytest.mark.parametrize("precision", [None, 2])
def test_format_thousands(formatter, decimal, precision):
    s = DataFrame([[1000000.123456789]]).style  # test float
    result = s.format(
        thousands="_", formatter=formatter, decimal=decimal, precision=precision
    )._translate(True, True)
    assert "1_000_000" in result["body"][0][1]["display_value"]

    s = DataFrame([[1000000]]).style  # test int
    result = s.format(
        thousands="_", formatter=formatter, decimal=decimal, precision=precision
    )._translate(True, True)
    assert "1_000_000" in result["body"][0][1]["display_value"]

    s = DataFrame([[1 + 1000000.123456789j]]).style  # test complex
    result = s.format(
        thousands="_", formatter=formatter, decimal=decimal, precision=precision
    )._translate(True, True)
    assert "1_000_000" in result["body"][0][1]["display_value"]


@pytest.mark.parametrize("formatter", [None, "{:,.4f}"])
@pytest.mark.parametrize("thousands", [None, ",", "*"])
@pytest.mark.parametrize("precision", [None, 4])
def test_format_decimal(formatter, thousands, precision):
    s = DataFrame([[1000000.123456789]]).style  # test float
    result = s.format(
        decimal="_", formatter=formatter, thousands=thousands, precision=precision
    )._translate(True, True)
    assert "000_123" in result["body"][0][1]["display_value"]

    s = DataFrame([[1 + 1000000.123456789j]]).style  # test complex
    result = s.format(
        decimal="_", formatter=formatter, thousands=thousands, precision=precision
    )._translate(True, True)
    assert "000_123" in result["body"][0][1]["display_value"]


def test_str_escape_error():
    msg = "`escape` only permitted in {'html', 'latex'}, got "
    with pytest.raises(ValueError, match=msg):
        _str_escape("text", "bad_escape")

    with pytest.raises(ValueError, match=msg):
        _str_escape("text", [])

    _str_escape(2.00, "bad_escape")  # OK since dtype is float


def test_format_options():
    df = DataFrame({"int": [2000, 1], "float": [1.009, None], "str": ["&<", "&~"]})
    ctx = df.style._translate(True, True)

    # test option: na_rep
    assert ctx["body"][1][2]["display_value"] == "nan"
    with option_context("styler.format.na_rep", "MISSING"):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][1][2]["display_value"] == "MISSING"

    # test option: decimal and precision
    assert ctx["body"][0][2]["display_value"] == "1.009000"
    with option_context("styler.format.decimal", "_"):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][0][2]["display_value"] == "1_009000"
    with option_context("styler.format.precision", 2):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][0][2]["display_value"] == "1.01"

    # test option: thousands
    assert ctx["body"][0][1]["display_value"] == "2000"
    with option_context("styler.format.thousands", "_"):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][0][1]["display_value"] == "2_000"

    # test option: escape
    assert ctx["body"][0][3]["display_value"] == "&<"
    assert ctx["body"][1][3]["display_value"] == "&~"
    with option_context("styler.format.escape", "html"):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][0][3]["display_value"] == "&amp;&lt;"
    with option_context("styler.format.escape", "latex"):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][1][3]["display_value"] == "\\&\\textasciitilde "

    # test option: formatter
    with option_context("styler.format.formatter", {"int": "{:,.2f}"}):
        ctx_with_op = df.style._translate(True, True)
        assert ctx_with_op["body"][0][1]["display_value"] == "2,000.00"


def test_precision_zero(df):
    styler = Styler(df, precision=0)
    ctx = styler._translate(True, True)
    assert ctx["body"][0][2]["display_value"] == "-1"
    assert ctx["body"][1][2]["display_value"] == "-1"


@pytest.mark.parametrize(
    "formatter, exp",
    [
        (lambda x: f"{x:.3f}", "9.000"),
        ("{:.2f}", "9.00"),
        ({0: "{:.1f}"}, "9.0"),
        (None, "9"),
    ],
)
def test_formatter_options_validator(formatter, exp):
    df = DataFrame([[9]])
    with option_context("styler.format.formatter", formatter):
        assert f" {exp} " in df.style.to_latex()


def test_formatter_options_raises():
    msg = "Value must be an instance of"
    with pytest.raises(ValueError, match=msg):
        with option_context("styler.format.formatter", ["bad", "type"]):
            DataFrame().style.to_latex()


def test_1level_multiindex():
    # GH 43383
    midx = MultiIndex.from_product([[1, 2]], names=[""])
    df = DataFrame(-1, index=midx, columns=[0, 1])
    ctx = df.style._translate(True, True)
    assert ctx["body"][0][0]["display_value"] == 1
    assert ctx["body"][0][0]["is_visible"] is True
    assert ctx["body"][1][0]["display_value"] == 2
    assert ctx["body"][1][0]["is_visible"] is True
