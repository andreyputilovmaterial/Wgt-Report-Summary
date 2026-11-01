"""Summarize HTML weighting reports into a compact CSV.

Parses an HTML report produced by the Unicom/IBM Professional weighting tool
and writes a CSV summary (one row per weighting group/filter), highlighting
failed groups and "impossible" (zero -> non-zero) or "extreme" cells.
"""

import re
import argparse
from pathlib import Path
import traceback, sys  # for error reporting - to print to stderr
import math
from datetime import datetime
from collections import namedtuple
from typing import Any, Iterable, Iterator, List, Optional, Union

from bs4 import BeautifulSoup, NavigableString


# One parsed weighting group/filter.
Record = namedtuple(
    "Record",
    ['wgt_filter', 'weight_var', 'matrix_vars', 'status', 'rim_limit',
     'summary_table', 'unw_base', 'wgt_base', 'weighting_efficiency'],
)


def make_output_name(fname: str, config: Optional[dict] = None) -> str:
    """Build the default output CSV name for an input report.

    Uses the input stem plus an ``MM.DD.YYYY`` timestamp from the run start time.
    """
    if config is None:
        config = {}
    today_americanstyle_str = config['time_start'].strftime('%m.%d.%Y')
    p = Path(fname)
    report_fname = p.with_stem(f"{p.stem}-summary-{today_americanstyle_str}").with_suffix('.csv')
    return safe_escape_quotes_csv(report_fname)


def safe_math_op_div(a: Any, b: Any) -> Union[float, str]:
    """Divide ``a`` by ``b``, returning the error text instead of raising."""
    try:
        return float(a) / float(b)
    except Exception as e:
        return safe_convert_txt(e)


def safe_round(c: Any) -> str:
    """Format a value to two decimals, falling back to its text form."""
    try:
        return f'{c:.2f}'
    except Exception:
        return safe_convert_txt(c)


def safe_convert_txt(c: Any) -> str:
    """Coerce any value to its string form."""
    return f'{c}'


def safe_is_nonnegative_number(c: Any) -> bool:
    """Return True if ``c`` is a non-negative number, False otherwise.

    Never raises: guards the summary-cell index comparison so an unexpected
    non-numeric value falls back to ``#Other`` instead of crashing.
    """
    try:
        return float(c) >= 0
    except (TypeError, ValueError):
        return False


def safe_escape_quotes_csv(c: Any) -> str:
    """Escape a value for a CSV cell.

    Doubles embedded double-quotes and prefixes a leading dash with an
    apostrophe (a workaround for Excel treating a leading ``-`` as a formula).
    """
    c = safe_convert_txt(c).replace('"','""')
    if c.startswith('-'):
        c = '\''+c
    return c


def is_html_layout_dumpster(html: str) -> bool:
    """Return True if the report has the broken multi-body layout we must fix."""
    body_tags = re.findall(r'<\s*?body\b.*?>',html,flags=re.I)
    if len(body_tags)>1:
        return True
    if re.match(r'^.*Weighting filter.*<\s*html',html,flags=re.I):
        return True
    return False


def fix_wgt_report_html(html: str) -> str:
    """Wrap broken report HTML in one body and rename nested html/body/head tags."""
    return '<html><body style="background: #6699cc;">'+re.sub(r'(<\s*?/?\s*?)((?:html|body|head))',lambda m: f'{m[1]}SECTION{m[2]}',html,flags=re.I)+'</body></html>'


def read_html(filename: str, config: Optional[dict] = None) -> List[str]:
    """Read a report file and normalize it into text lines.

    Collapses whitespace, repairs the broken layout when needed, converts each
    ``<tr>`` into a tab-separated row, and returns the resulting lines.
    """
    with open(filename, "r", encoding="utf-8") as f:
        contents = f.read()
        if is_html_layout_dumpster(contents):
            contents = fix_wgt_report_html(contents)
        contents_normalized = re.sub(r'\s+',' ',contents)
        soup = BeautifulSoup(contents_normalized, "html.parser")
        for tr in soup.find_all('tr'):
            converted_str = ''
            for cell_num, td in enumerate(tr.find_all(['td','th'])):
                converted_str += ('\t' if cell_num>0 else '') + td.get_text(strip=True)
            tr.replace_with(NavigableString(converted_str))
        text = soup.get_text("\n")
        return text.splitlines()


def read_txt(filename: str, config: Optional[dict] = None) -> Iterator[str]:
    """Yield lines from a text file (kept for completeness; reports are HTML)."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                yield line
    except FileNotFoundError as e:
        raise e


def parse_log(lines: Iterable[str], config: Optional[dict] = None) -> List[Record]:
    """Parse normalized report lines into one ``Record`` per weighting filter."""
    def clean_summary_outputs_value(d):
        if d == '------':
            return 0
        if d == '-nan(ind)':
            return float('nan')
        # The summary-table regex only admits numbers, dashes and -nan(ind), but
        # stay defensive: an unparseable value becomes NaN (an "Impossible" row)
        # rather than crashing the whole run.
        try:
            return float(d)
        except (ValueError, TypeError):
            return float('nan')


    current_group_wgt_filter = None
    matrix_vars = None
    has_error = False
    weight_var = None
    rms = None
    unw_base = None
    wgt_base = None
    weighting_efficiency = None
    is_within_summary_table = False
    summary_table = None
    summary_curr_table_var_index = None
    summary_table_curr_cell_index = None
    summary_table_was_last_line_a_separator = None
    results = []

    for line in lines:

        m = re.match(r'^\s*?weighting filter:\s*(.+)', line,flags=re.I)
        if m:
            if current_group_wgt_filter:
                results.append(Record(
                    wgt_filter = current_group_wgt_filter,
                    weight_var = weight_var,
                    matrix_vars = matrix_vars,
                    status = "FAILED" if has_error else "OK",
                    rim_limit = rms,
                    summary_table = summary_table,
                    unw_base = unw_base,
                    wgt_base = wgt_base,
                    weighting_efficiency = weighting_efficiency,
                ))
            current_group_wgt_filter = m.group(1)
            has_error = False
            rms = None
            is_within_summary_table = False
            summary_table = None
            weight_var = None
            continue

        if re.search(r'(?:failure|error)', line, re.I):
            has_error = True
            rms = None
        # Convergence occurred on iteration 12 with rms 663.238766 limit
        if re.search(r'Convergence occurred on iteration .*? with rms\b\s*(\d+(?:\.\d+)?|\.\d+)\s*\blimit', line, re.I):
            rms = re.match(r'Convergence occurred on iteration .*? with rms\b\s*(\d+(?:\.\d+)?|\.\d+)\s*\blimit', line)[1]
        
        m = re.match(r'^\s*?matrix vars:\s*(.*)', line,flags=re.I)
        if m:
            matrix_vars = m.group(1).split()
        
        m = re.match(r'^\s*?Weight var:\s*(.*)', line, flags=re.I)
        if m:
            weight_var = m.group(1)

        m = re.match(r'^\s*?Rim weighting efficiency\s*(.*)', line, flags=re.I)
        if m:
            weighting_efficiency = m.group(1)

        if is_within_summary_table:
            m = re.match(r'^\s*?(------|\d+(?:\.\d+)?|-nan\(ind\))\s*?\t\s*?(------|\d+(?:\.\d+)?|-nan\(ind\))\s*?\t\s*?(------|\d+(?:\.\d+)?|-nan\(ind\))\s*?\t\s*?(------|\d+(?:\.\d+)?|-nan\(ind\))\s*?$', line, re.I)
            if m:
                the_var = '???'
                try:
                    the_var = matrix_vars[summary_curr_table_var_index]
                except (IndexError, TypeError):
                    the_var = '???'
                perc_inp = clean_summary_outputs_value(m.group(2))
                perc_proj = clean_summary_outputs_value(m.group(4))
                ratio = 1 if perc_inp == 0 and perc_proj == 0 else float('nan') if math.isnan(perc_inp) or math.isnan(perc_proj) else perc_proj/perc_inp if perc_inp>0 and perc_proj>0 else float('nan')
                summary_table.append((
                    the_var,
                    summary_table_curr_cell_index,
                    m.group(1),
                    m.group(2),
                    m.group(3),
                    m.group(4),
                    ratio,
                ))
                if summary_table_was_last_line_a_separator:
                    unw_base = clean_summary_outputs_value(m.group(1))
                    wgt_base = clean_summary_outputs_value(m.group(3))
                summary_table_curr_cell_index += 1
                if re.match(r'^\s*?(------)\s*?\t\s*?(------)\s*?\t\s*?(------)\s*?\t\s*?(------)\s*?$', line, re.I):
                    summary_table_curr_cell_index = -1000
                if summary_table_was_last_line_a_separator:
                    summary_curr_table_var_index += 1
                    summary_table_curr_cell_index = 0
                summary_table_was_last_line_a_separator = not not re.match(r'^\s*?(------)\s*?\t\s*?(------)\s*?\t\s*?(------)\s*?\t\s*?(------)\s*?$', line, re.I)
            else:
                if re.match(r'^\s*$',line):
                    pass
                else:
                    is_within_summary_table = False
        if re.search(r'^\s*?Input frequency\s*?\t\s*?Input percent\s*?\t\s*?Projected frequency\s*?\t\s*?Projected percent\s*?$', line, re.I):
            is_within_summary_table = True
            summary_table = []
            summary_curr_table_var_index = 0
            summary_table_curr_cell_index = 0

    if current_group_wgt_filter:
        results.append(Record(
            wgt_filter = current_group_wgt_filter,
            weight_var = weight_var,
            matrix_vars = matrix_vars,
            status = "FAILED" if has_error else "OK",
            rim_limit = rms,
            summary_table = summary_table,
            unw_base = unw_base,
            wgt_base = wgt_base,
            weighting_efficiency = weighting_efficiency,
        ))

    return results

def write_results(report_fname: str, results: List[Record], config: Optional[dict] = None) -> None:
    """Write parsed records to a CSV summary file.

    Honors ``options.out_append`` (append instead of overwrite, header only when
    new/empty) and ``options.out_reportfile_stats`` (prepend ``Report File`` and
    ``Last Edited`` columns).
    """
    if config is None:
        config = {}
    options = config.get('options', {})
    out_append = bool(options.get('out_append'))
    out_reportfile_stats = bool(options.get('out_reportfile_stats'))

    # In append mode we reuse an existing CSV, so only write the header when
    # the file is new or empty - otherwise the header would be duplicated.
    need_write_header = (not out_append) or (not Path(report_fname).exists() or Path(report_fname).stat().st_size == 0)

    # When requested, prepend two identifying columns so every row can be
    # traced back to the source report file (and its last-edit timestamp).
    input_filename_mtime = '???'
    try:
        input_filename_mtime = datetime.fromtimestamp(Path(config['input_filename']).stat().st_mtime).isoformat()
    except Exception as e:
        input_filename_mtime = safe_convert_txt(e)

    if out_reportfile_stats:
        header_prepend = '"{cellprepend1}","{cellprepend2}",'.format(
            cellprepend1 = safe_escape_quotes_csv('Report File'),
            cellprepend2 = safe_escape_quotes_csv('Last Edited'),
        )
        row_prepend = '"{cellprepend1}","{cellprepend2}",'.format(
            cellprepend1 = safe_escape_quotes_csv(Path(config['input_filename']).stem),
            cellprepend2 = safe_escape_quotes_csv(input_filename_mtime),
        )
    else:
        header_prepend = ''
        row_prepend = ''

    with open(report_fname, 'a' if out_append else 'w', encoding='utf-8') as out:
        if need_write_header:
            out.write('{cols_prepend}"{cell1}","{cell2}","{cell3}","{cell4}","{cell5}","{cell6}","{cell7}"\n'.format(
                cols_prepend = header_prepend,
                cell1 = safe_escape_quotes_csv('Filter'),
                cell2 = safe_escape_quotes_csv('Weight Var'),
                cell3 = safe_escape_quotes_csv('Status'),
                cell4 = safe_escape_quotes_csv('Rim Limit'),
                cell5 = safe_escape_quotes_csv('Weighting Efficiency'),
                cell6 = safe_escape_quotes_csv('Impossible'),
                cell7 = safe_escape_quotes_csv('Extreme'),
            ))
        for wgt_filter, weight_var, matrix_vars, status, rim_limit, summary_table, unw_base, wgt_base, weighting_efficiency in results:
            if summary_table is None:
                # No summary table: leave both cells empty (they hold
                # comma-separated lists, and an empty list == empty cell).
                impossible_txt = ''
                extreme_txt = ''
            else:
                bad_rows = [ r for r in summary_table if math.isnan(r[6]) ]
                extreme_rows = [ r for r in summary_table if not math.isnan(r[6]) and not ( (r[6]>.32) and (r[6]<3.2) ) ]
                impossible_txt = ', '.join([ '{v} / Cell{n} ({m2}% -> {m4}%)'.format(v=r[0],n=r[1]+1 if safe_is_nonnegative_number(r[1]) else '#Other',m2=r[3],m4=r[5]) for r in bad_rows ])
                extreme_txt = ', '.join([ '{v} / Cell{n} ({m2}% -> {m4}% = {ratio}x)'.format(v=r[0],n=r[1]+1 if safe_is_nonnegative_number(r[1]) else '#Other',m2=r[3],m4=r[5],ratio=safe_round(r[6])) for r in extreme_rows ])
            out.write('{cols_prepend}"{cell1}","{cell2}","{cell3}","{cell4}","{cell5}","{cell6}","{cell7}"\n'.format(
                cols_prepend = row_prepend,
                cell1 = safe_escape_quotes_csv(wgt_filter),
                cell2 = safe_escape_quotes_csv(weight_var),
                cell3 = safe_escape_quotes_csv(status),
                cell4 = safe_escape_quotes_csv(rim_limit if rim_limit is None else '{xxx} x {nnn}n = {rms}'.format(rms=safe_round(rim_limit),nnn=safe_round(unw_base),xxx=safe_round(safe_math_op_div(rim_limit,unw_base)))),
                cell5 = safe_escape_quotes_csv(weighting_efficiency),
                cell6 = safe_escape_quotes_csv(impossible_txt),
                cell7 = safe_escape_quotes_csv(extreme_txt),
            ))
    


def main() -> None:
    """CLI entry point: parse args, read one report, and write the summary CSV."""
    try:
        time_start = datetime.now()
        parser = argparse.ArgumentParser(
            description="Summarize log sections by filter and error status",
            prog='wgt_summary',
        )
        parser.add_argument(
            "--file",
            "-f",
            required=False,
            help="Path to the log file to analyze",
            default = 'Weight_Report.htm',
        )
        parser.add_argument(
            "-o",
            "--out",
            required=False,
            help="Output summary file, CSV"
        )
        parser.add_argument(
            "--options",
            required=False,
            help="Comma-separated output flags: out_append, out_reportfile_stats"
        )

        args = parser.parse_args()

        config = {}
        config['time_start'] = time_start
        config['options'] = {}

        fname = Path(args.file)
        fname = fname.resolve()
        if not fname.is_file():
            raise FileNotFoundError(f'{fname} not found')
        fname = safe_convert_txt(fname)
        
        report_fname = None
        if args.out:
            report_fname = args.out
        else:
            report_fname = make_output_name(fname,config)
        report_fname = Path(report_fname).resolve()
        report_fname = safe_convert_txt(report_fname)

        if args.options:
            for flag in [f.strip() for f in args.options.split(',')]:
                if flag == 'out_append':
                    config['options']['out_append'] = True
                elif flag == 'out_reportfile_stats':
                    config['options']['out_reportfile_stats'] = True
                else:
                    raise Exception('unrecognized options flag: {f}'.format(f=flag))

        print('{script}: script started at {dt}'.format(dt=time_start,script=parser.prog))

        config['input_filename'] = fname
        config['output_filename'] = report_fname

        print('reading {f}'.format(f=fname))
        results = parse_log(read_html(safe_convert_txt(fname),config),config)

        print(f"Writing results to: {report_fname}")
        write_results(report_fname,results,config)

        time_finish = datetime.now()
        print('{script}: finished at {dt} (elapsed {duration})'.format(script=parser.prog,dt=time_finish,duration=time_finish-time_start))

    except Exception as e:
        # the program is designed to be user-friendly
        # that's why we reformat error messages a little bit
        # stack trace is still printed (I even made it longer to 20 steps!)
        # but the error message itself is separated and printed as the last message again

        # for example, I don't write "print('File Not Found!');exit(1);", I just write "raise FileNotFoundErro()"
        print('',file=sys.stderr)
        print('Stack trace:',file=sys.stderr)
        print('',file=sys.stderr)
        traceback.print_exception(e,limit=20)
        print('',file=sys.stderr)
        print('',file=sys.stderr)
        print('',file=sys.stderr)
        print('Error:',file=sys.stderr)
        print('',file=sys.stderr)
        print('{e}'.format(e=e),file=sys.stderr)
        print('',file=sys.stderr)
        exit(1)


if __name__ == "__main__":
    main()
