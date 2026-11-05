@ECHO OFF

REM ============================================================================
REM  Wgt-Report-Summary - Example 1: process a single weight report.
REM
REM  Simplest usage: run the script on one HTML report and let it write a
REM  summary CSV next to it (the CSV name is derived from the report name).
REM
REM  SCRIPT_PATH points to run_wgt_summary.py. In this repo the script lives
REM  under src\, so SCRIPT_PATH is "..\src\run_wgt_summary.py". A release build
REM  (build.sh / build.bat) copies this wrapper into dist\ and rewrites
REM  SCRIPT_PATH to "run_wgt_summary.py" (the .py sits next to the wrapper).
REM ============================================================================

REM ---- Most important: the folder that holds the report. ---------------------
set "REPORT_DIR=."

REM ---- Other settings. ------------------------------------------------------
set "REPORT_FILE=Weight_Report.htm"
set "SCRIPT_PATH=..\src\run_wgt_summary.py"

REM Resolve the report folder to an absolute path and show it, so it is clear
REM where the program is looking for the report.
for %%I in ("%REPORT_DIR%") do set "REPORT_DIR=%%~fI"
echo Looking for reports in: %REPORT_DIR%

echo Processing %REPORT_DIR%\%REPORT_FILE% ...
python "%SCRIPT_PATH%" --file "%REPORT_DIR%\%REPORT_FILE%"
if errorlevel 1 (
    echo FAILED while processing %REPORT_DIR%\%REPORT_FILE%
    pause
    exit /b 1
)
