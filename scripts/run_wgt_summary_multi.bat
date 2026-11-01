@ECHO OFF

REM ============================================================================
REM  Wgt-Report-Summary - Example 2: append several reports explicitly.
REM
REM  Run the script once per report, all pointing at the SAME output file with
REM  --options out_append,out_reportfile_stats. Each run appends its rows, so you
REM  end up with one combined CSV across all reports. Edit the REPORT lines below
REM  to match your real file names.
REM
REM  In a release, run_wgt_summary.py sits in the same folder as this .bat, so
REM  SCRIPT can simply be "run_wgt_summary.py". In this repo the script lives
REM  under src\, hence the "..\src\" prefix. Update SCRIPT to match your layout.
REM ============================================================================

set "SCRIPT=..\src\run_wgt_summary.py"
set "OUT=Weight_Summary.csv"

REM Start from a clean output file.
if exist "%OUT%" del "%OUT%"

python "%SCRIPT%" --file "Weight_Report_DE.htm" --out "%OUT%" --options out_append,out_reportfile_stats
if errorlevel 1 (
    echo ERROR: Failure while processing Weight_Report_DE.htm
    pause
    exit /b 1
)

python "%SCRIPT%" --file "Weight_Report_FR.htm" --out "%OUT%" --options out_append,out_reportfile_stats
if errorlevel 1 (
    echo ERROR: Failure while processing Weight_Report_FR.htm
    pause
    exit /b 1
)

python "%SCRIPT%" --file "Weight_Report_UK.htm" --out "%OUT%" --options out_append,out_reportfile_stats
if errorlevel 1 (
    echo ERROR: Failure while processing Weight_Report_UK.htm
    pause
    exit /b 1
)

echo Done. Combined summary written to: %OUT%
