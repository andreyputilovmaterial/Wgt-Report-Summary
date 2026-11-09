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
                 weighting_efficiency=None, integrity_error=None):
    # Field order matches the Record namedtuple produced by parse_log().
    return (wgt_filter, weight_var, matrix_vars if matrix_vars is not None else [],
            status, rim_limit, summary_table, unw_base, wgt_base, weighting_efficiency,
            integrity_error)


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

def test_write_results_default_eight_columns(tmp_path):
    out = tmp_path / "out.csv"
    results = [_make_result(wgt_filter="F", summary_table=[])]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # header + one data row
    assert lines[0].split(",") == ['"Filter"', '"Weight Var"', '"Status"', '"Rim Limit"',
                                   '"Weighting Efficiency"', '"Impossible"', '"Extreme"',
                                   '"Furthest from target"']


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


def test_write_results_returns_row_count(tmp_path):
    out = tmp_path / "out.csv"
    results = [_make_result(wgt_filter="F", summary_table=[])]
    config = {"input_filename": str(tmp_path / "x.htm"), "options": {}}
    assert rws.write_results(str(out), results, config) == 1
    assert rws.write_results(str(out), [], config) == 0


def test_write_results_append_empty_results_writes_nothing(tmp_path):
    out = tmp_path / "out.csv"
    results = [_make_result(wgt_filter="F", summary_table=[])]
    config = {"input_filename": str(tmp_path / "x.htm"), "options": {"out_append": True}}
    rws.write_results(str(out), results, config)
    before = out.read_text(encoding="utf-8")
    # Appending zero rows to an existing non-empty CSV must not touch it, so a
    # caller can truthfully report "nothing written".
    assert rws.write_results(str(out), [], config) == 0
    assert out.read_text(encoding="utf-8") == before


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


# ---------------------------------------------------------------------------
# Rim weight / Output frequency / Output percent + "Furthest from target"
# ---------------------------------------------------------------------------

def test_parse_log_attaches_rim_weight_output_percent():
    lines = [
        "Weighting filter: F",
        "Weight var: W",
        "Matrix vars: A B",
        "Input frequency\tInput percent\tProjected frequency\tProjected percent",
        "94.000\t51.65\t81.383\t50.78",      # A target 0
        "88.000\t48.35\t78.883\t49.22",      # A target 1
        "------\t------\t------\t------",     # A dashed
        "182.000\t100.00\t160.266\t100.00",  # A total
        "60.000\t60.00\t59.400\t59.40",      # B target 0
        "40.000\t40.00\t39.600\t39.60",      # B target 1
        "------\t------\t------\t------",     # B dashed
        "100.000\t100.00\t99.000\t99.00",    # B total
        "Rim weight\tOutput frequency\tOutput percent",
        "1.24\t79.877\t49.84",               # A target 0 -> 49.84
        "0.63\t80.388\t50.16",               # A target 1 -> 50.16
        "\t------\t------",                  # A dashed
        "\t160.265\t100.00",                 # A total
        "1.10\t58.000\t58.00",               # B target 0 -> 58.00
        "0.90\t38.000\t38.00",               # B target 1 -> 38.00
        "\t------\t------",                  # B dashed
        "\t99.000\t99.00",                   # B total
        "Rim weighting efficiency 84.8%",
    ]
    results = rws.parse_log(lines, {})
    assert len(results) == 1
    r = results[0]
    assert r.integrity_error is None
    assert r.summary_table[0][7] == 49.84
    assert r.summary_table[1][7] == 50.16
    assert r.summary_table[2][7] == 0.0
    assert r.summary_table[3][7] == 100.0
    assert r.summary_table[4][7] == 58.0
    assert r.summary_table[5][7] == 38.0
    assert r.summary_table[6][7] == 0.0
    assert r.summary_table[7][7] == 99.0


def test_write_results_furthest_from_target_column(tmp_path):
    out = tmp_path / "out.csv"
    table = [
        ("A", 0, "94.000", "51.65", "81.383", "50.78", 1.0, 49.84),
        ("A", 1, "88.000", "48.35", "78.883", "49.22", 1.0, 50.16),
        ("B", 0, "60.000", "60.00", "59.400", "59.40", 1.0, 58.00),
        ("B", 1, "40.000", "40.00", "39.600", "39.60", 1.0, 38.00),
    ]
    results = [_make_result(wgt_filter="F", summary_table=table)]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    text = out.read_text(encoding="utf-8")
    assert 'B / Cell2 (target 39.60% -> achieved 38.00% = -1.60pp)' in text
    assert 'B / Cell1 (target 59.40% -> achieved 58.00% = -1.40pp)' in text
    assert 'A / Cell1 (target 50.78% -> achieved 49.84% = -0.94pp)' in text
    # ranked by absolute gap: the -0.94pp row must come after the -1.60/-1.40 rows
    assert text.index('B / Cell2') < text.index('B / Cell1') < text.index('A / Cell1')


def test_parse_log_rim_weight_row_count_mismatch_sets_integrity_error():
    lines = [
        "Weighting filter: F",
        "Weight var: W",
        "Matrix vars: A B",
        "Input frequency\tInput percent\tProjected frequency\tProjected percent",
        "94.000\t51.65\t81.383\t50.78",
        "------\t------\t------\t------",
        "182.000\t100.00\t160.266\t100.00",
        "60.000\t60.00\t59.400\t59.40",
        "------\t------\t------\t------",
        "100.000\t100.00\t99.000\t99.00",
        # Rim weight table only covers rim A (3 rows), not rim B.
        "Rim weight\tOutput frequency\tOutput percent",
        "1.24\t79.877\t49.84",
        "\t------\t------",
        "\t160.265\t100.00",
        "Rim weighting efficiency 84.8%",
    ]
    results = rws.parse_log(lines, {})
    assert results[0].integrity_error == "row count mismatch (summary 6 vs rim weights 3)"


def test_parse_log_rim_weight_structure_mismatch_sets_integrity_error():
    lines = [
        "Weighting filter: F",
        "Weight var: W",
        "Matrix vars: A",
        "Input frequency\tInput percent\tProjected frequency\tProjected percent",
        "94.000\t51.65\t81.383\t50.78",
        "------\t------\t------\t------",
        "182.000\t100.00\t160.266\t100.00",
        # Row 2 is a target where the summary has a dashed separator row.
        "Rim weight\tOutput frequency\tOutput percent",
        "1.24\t79.877\t49.84",
        "0.63\t80.388\t50.16",
        "\t160.265\t100.00",
        "Rim weighting efficiency 84.8%",
    ]
    results = rws.parse_log(lines, {})
    assert "structure mismatch at row 2" in results[0].integrity_error


def test_furthest_from_target_skips_malformed_values():
    rows = [
        ("A", 0, "94.000", "51.65", "81.383", "50.78", 1.0, 49.84),
        ("B", 1, "88.000", "48.35", "78.883", "not-a-number", 1.0, 50.16),
        ("C", 2, "60.000", "60.00", "59.400", "59.40", 1.0, float("nan")),
    ]
    txt = rws.furthest_from_target(rows, None, 3)
    assert "A / Cell1" in txt
    assert "B / Cell2" not in txt
    assert "C / Cell3" not in txt


def test_furthest_from_target_integrity_error_and_missing_table():
    assert rws.furthest_from_target([], "row count mismatch", 3) == "#N/A: row count mismatch"
    assert rws.furthest_from_target(None, None, 3) == ""


def test_write_results_furthest_integrity_error_shows_na(tmp_path):
    out = tmp_path / "out.csv"
    table = [
        ("A", 0, "94.000", "51.65", "81.383", "50.78", 1.0, 49.84),
    ]
    results = [_make_result(wgt_filter="F", summary_table=table, integrity_error="row count mismatch")]
    rws.write_results(str(out), results, {"input_filename": str(tmp_path / "x.htm"), "options": {}})
    text = out.read_text(encoding="utf-8")
    assert "#N/A: row count mismatch" in text
