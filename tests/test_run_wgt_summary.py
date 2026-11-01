import math
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import run_wgt_summary as rws


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summary_row(the_var, cell_index, inp_freq, inp_perc, proj_freq, proj_perc, ratio):
    return (the_var, cell_index, inp_freq, inp_perc, proj_freq, proj_perc, ratio)


def _make_result(wgt_filter="F", weight_var="W", matrix_vars=None, status="OK",
                 rim_limit=None, summary_table=None, unw_base=None, wgt_base=None,
                 weighting_efficiency=None):
    # Field order matches the Record namedtuple produced by parse_log().
    return (wgt_filter, weight_var, matrix_vars if matrix_vars is not None else [],
            status, rim_limit, summary_table, unw_base, wgt_base, weighting_efficiency)


def _minimal_report_lines():
    return [
        "Weighting filter: DV_FLAG_MARKET.ContainsAny({DE})",
        "Weight var: Weight_Completes",
        "Matrix vars: DV_FLAG_AGEGENDER_WGT DV_SampleType",
        "Input frequency\tInput percent\tProjected frequency\tProjected percent",
        "94.000\t51.65\t81.383\t50.78",
        "88.000\t48.35\t78.883\t49.22",
        "------\t------\t------\t------",
        "182.000\t100.00\t160.266\t100.00",
        "Rim weighting efficiency 84.8%",
    ]


# ---------------------------------------------------------------------------
# parse_log
# ---------------------------------------------------------------------------

def test_parse_log_basic_report():
    results = rws.parse_log(_minimal_report_lines(), {})
    assert len(results) == 1
    r = results[0]
    assert r.wgt_filter == "DV_FLAG_MARKET.ContainsAny({DE})"
    assert r.weight_var == "Weight_Completes"
    assert r.matrix_vars == ["DV_FLAG_AGEGENDER_WGT", "DV_SampleType"]
    assert r.status == "OK"
    assert r.weighting_efficiency == "84.8%"
    assert r.unw_base == 182.0
    assert r.wgt_base == 160.266
    assert len(r.summary_table) == 4


def test_parse_log_no_summary_table_sets_none():
    lines = [
        "Weighting filter: DV_FLAG_MARKET.ContainsAny({DE})",
        "Weight var: Weight_Completes",
        "Matrix vars: DV_FLAG_AGEGENDER_WGT",
        # No "Input frequency" header line -> no summary table parsed.
    ]
    results = rws.parse_log(lines, {})
    assert len(results) == 1
    assert results[0].summary_table is None


# ---------------------------------------------------------------------------
# write_results
# ---------------------------------------------------------------------------

def test_write_results_default_seven_columns(tmp_path):
    out = tmp_path / "out.csv"
    results = [_make_result(wgt_filter="F", summary_table=[])]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # header + one data row
    assert lines[0].split(",") == ['"Filter"', '"Weight Var"', '"Status"', '"Rim Limit"',
                                   '"Weighting Efficiency"', '"Impossible"', '"Extreme"']


def test_write_results_no_summary_table_leaves_cells_empty(tmp_path):
    out = tmp_path / "out.csv"
    results = [_make_result(summary_table=None)]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    lines = out.read_text(encoding="utf-8").splitlines()
    # Regression: this used to crash while iterating a fallback tuple; now it
    # just leaves the Impossible/Extreme cells empty.
    assert len(lines) == 2  # header + one data row
    assert lines[1].endswith(',"",""')
    assert "Exception: no table parsed" not in lines[1]


def test_read_parse_write_filter_without_summary_table_does_not_crash(tmp_path):
    # End-to-end regression for issue #1: a weighting filter with no summary
    # table (e.g. a failed rim) used to crash write_results with
    # "TypeError: '>=' not supported between instances of 'str' and 'int'".
    html = tmp_path / "Weight_Report.htm"
    html.write_text(
        "<html><body>"
        "<P>Weighting filter: F1<BR>"
        "Weight var: Weight_Completes<BR>"
        "Matrix vars: A B<BR>"
        "failure on rims<BR>"
        "</body></html>",
        encoding="utf-8",
    )
    lines = rws.read_html(str(html), {})
    results = rws.parse_log(lines, {})
    assert len(results) == 1
    assert results[0].summary_table is None

    out = tmp_path / "out.csv"
    rws.write_results(str(out), results, {"input_filename": str(html), "options": {}})
    rows = out.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2  # header + one data row
    assert rows[1].endswith(',"",""')


def test_write_results_impossible_and_extreme(tmp_path):
    out = tmp_path / "out.csv"
    table = [
        _summary_row("VAR", 0, "100.000", "10.00", "80.000", "8.00", math.nan),
        _summary_row("VAR", 1, "50.000", "50.00", "60.000", "60.00", 1.2),
        _summary_row("VAR", 2, "40.000", "40.00", "200.000", "50.00", 3.5),
    ]
    results = [_make_result(wgt_filter="F", summary_table=table)]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    text = out.read_text(encoding="utf-8")
    assert "VAR / Cell1 (10.00% -> 8.00%)" in text
    assert "VAR / Cell3 (40.00% -> 50.00% = 3.50x)" in text


def test_safe_is_nonnegative_number():
    assert rws.safe_is_nonnegative_number(0) is True
    assert rws.safe_is_nonnegative_number(17) is True
    assert rws.safe_is_nonnegative_number(-1000) is False
    assert rws.safe_is_nonnegative_number("17") is True
    assert rws.safe_is_nonnegative_number("unexpected") is False
    assert rws.safe_is_nonnegative_number(None) is False


def test_write_results_non_numeric_cell_index_does_not_crash(tmp_path):
    out = tmp_path / "out.csv"
    table = [_summary_row("VAR", "unexpected", "100.000", "0.00", "80.000", "8.00", math.nan)]
    results = [_make_result(wgt_filter="F", summary_table=table)]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    text = out.read_text(encoding="utf-8")
    # A non-numeric cell index must fall back to '#Other' instead of raising.
    assert "VAR / Cell#Other (0.00% -> 8.00%)" in text


def test_write_results_append_writes_header_once(tmp_path):
    out = tmp_path / "out.csv"
    results = [_make_result(wgt_filter="F", summary_table=[])]
    config = {"input_filename": str(tmp_path / "x.htm"), "options": {"out_append": True}}
    rws.write_results(str(out), results, config)
    rws.write_results(str(out), results, config)
    text = out.read_text(encoding="utf-8")
    assert text.count('"Filter"') == 1
    assert text.count('"F"') == 2


def test_write_results_reportfile_stats_columns(tmp_path):
    out = tmp_path / "out.csv"
    src = tmp_path / "Weight_Report_DE.htm"
    src.write_text("<html></html>", encoding="utf-8")
    results = [_make_result(wgt_filter="F", summary_table=[])]
    config = {"input_filename": str(src), "options": {"out_reportfile_stats": True}}
    rws.write_results(str(out), results, config)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith('"Report File","Last Edited",')
    assert '"Weight_Report_DE",' in lines[1]


# ---------------------------------------------------------------------------
# read_html + parse_log integration
# ---------------------------------------------------------------------------

def test_read_html_and_parse_integration(tmp_path):
    html = tmp_path / "Weight_Report.htm"
    html.write_text(
        "<html><body>"
        "<P>Summary of weighting<BR>"
        "<P>Weighting filter: DV_FLAG_MARKET.ContainsAny({DE})<BR>"
        "Weight var: Weight_Completes<BR>"
        "Matrix vars: DV_FLAG_AGEGENDER_WGT DV_SampleType<BR>"
        "<P><TABLE>"
        "<TR><TD>Input frequency</TD><TD>Input percent</TD><TD>Projected frequency</TD><TD>Projected percent</TD></TR>"
        "<TR><TD>94.000</TD><TD>51.65</TD><TD>81.383</TD><TD>50.78</TD></TR>"
        "<TR><TD>------</TD><TD>------</TD><TD>------</TD><TD>------</TD></TR>"
        "<TR><TD>182.000</TD><TD>100.00</TD><TD>160.266</TD><TD>100.00</TD></TR>"
        "</TABLE>"
        "<P>Rim weighting efficiency 84.8%<BR>"
        "</body></html>",
        encoding="utf-8",
    )
    lines = rws.read_html(str(html), {})
    results = rws.parse_log(lines, {})
    assert len(results) == 1
    assert results[0].wgt_filter == "DV_FLAG_MARKET.ContainsAny({DE})"
    assert results[0].weighting_efficiency == "84.8%"


# ---------------------------------------------------------------------------
# Realistic anonymized sample + degenerate-input resilience
# ---------------------------------------------------------------------------

def test_read_html_and_parse_dummy_report():
    fixture = Path(__file__).parent / "fixtures" / "dummy_weight_report.htm"
    lines = rws.read_html(str(fixture), {})
    results = rws.parse_log(lines, {})
    assert len(results) == 2
    assert results[0].weight_var == "Weight_Target"
    assert "DEMO_WAVE" in results[0].wgt_filter
    assert results[0].matrix_vars == ["DV_GENDER", "DV_REGION", "DV_INCOME",
                                      "DV_SAMPLE", "DV_DEVICE", "DV_PROVIDER"]
    # The real variable names must not leak into the committed sample.
    assert "DV_FLAG_AGEGENDER_WGT" not in results[0].wgt_filter
    assert "Weight_Completes" not in results[0].weight_var


def test_parse_log_summary_table_without_matrix_vars_does_not_crash():
    lines = [
        "Weighting filter: F",
        "Weight var: W",
        # No "Matrix vars:" line -> matrix_vars stays None while a summary
        # table is still parsed; the cell must fall back to '???' instead of
        # raising a TypeError.
        "Input frequency\tInput percent\tProjected frequency\tProjected percent",
        "94.000\t51.65\t81.383\t50.78",
    ]
    results = rws.parse_log(lines, {})
    assert len(results) == 1
    assert results[0].summary_table[0][0] == "???"
