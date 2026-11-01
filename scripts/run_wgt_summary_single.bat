@ECHO OFF

REM ============================================================================
REM  Wgt-Report-Summary - Example 1: process a single weight report.
REM
REM  Simplest usage: run the script on one HTML report and let it write a
REM  summary CSV next to it.
REM
REM  In a release, run_wgt_summary.py sits in the same folder as this .bat, so
REM  SCRIPT can simply be "run_wgt_summary.py". In this repo the script lives
REM  under src\, hence the "..\src\" prefix. Update SCRIPT to match your layout.
REM ============================================================================

set "SCRIPT=..\src\run_wgt_summary.py"
set "REPORT=Weight_Report.htm"

python "%SCRIPT%" --file "%REPORT%"
if errorlevel 1 (
    echo ERROR: Failure while processing %REPORT%
    pause
    exit /b 1
)
