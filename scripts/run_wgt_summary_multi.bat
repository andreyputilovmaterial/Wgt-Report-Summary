@ECHO OFF

REM ============================================================================
REM  Wgt-Report-Summary - Example 2: append several reports explicitly.
REM
REM  Run the script once per report, all pointing at the SAME output file with
REM  --options out_append,out_reportfile_stats. Each run appends its rows, so you
REM  end up with one combined CSV across all reports. Edit the report names below
REM  to match your real files.
REM
REM  SCRIPT_PATH points to run_wgt_summary.py. In this repo the script lives
REM  under src\, so SCRIPT_PATH is "..\src\run_wgt_summary.py". A release build
REM  (build.sh / build.bat) copies this wrapper into dist\ and rewrites
REM  SCRIPT_PATH to "run_wgt_summary.py" (the .py sits next to the wrapper).
REM ============================================================================

REM ---- Most important: the folder that holds the reports. --------------------
set "REPORT_DIR=."

REM ---- Other settings. ------------------------------------------------------
set "OUTPUT_FILENAME=Weight_Summary.csv"
set "SCRIPT_PATH=..\src\run_wgt_summary.py"

REM Resolve the report folder to an absolute path and show it, so it is clear
REM where the program is looking for the reports.
for %%I in ("%REPORT_DIR%") do set "REPORT_DIR=%%~fI"
echo Looking for reports in: %REPORT_DIR%

REM Start from a clean output file.
if exist "%REPORT_DIR%\%OUTPUT_FILENAME%" del "%REPORT_DIR%\%OUTPUT_FILENAME%"

python "%SCRIPT_PATH%" --file "%REPORT_DIR%\Weight_Report_DE.htm" --out "%REPORT_DIR%\%OUTPUT_FILENAME%" --options out_append,out_reportfile_stats
if errorlevel 1 (
    echo FAILED while processing %REPORT_DIR%\Weight_Report_DE.htm
    pause
    exit /b 1
)

python "%SCRIPT_PATH%" --file "%REPORT_DIR%\Weight_Report_FR.htm" --out "%REPORT_DIR%\%OUTPUT_FILENAME%" --options out_append,out_reportfile_stats
if errorlevel 1 (
    echo FAILED while processing %REPORT_DIR%\Weight_Report_FR.htm
    pause
    exit /b 1
)

python "%SCRIPT_PATH%" --file "%REPORT_DIR%\Weight_Report_UK.htm" --out "%REPORT_DIR%\%OUTPUT_FILENAME%" --options out_append,out_reportfile_stats
if errorlevel 1 (
    echo FAILED while processing %REPORT_DIR%\Weight_Report_UK.htm
    pause
    exit /b 1
)

echo Done. Combined summary written to: %REPORT_DIR%\%OUTPUT_FILENAME%
