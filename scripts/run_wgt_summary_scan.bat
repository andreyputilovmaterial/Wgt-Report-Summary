@ECHO OFF
setlocal EnableDelayedExpansion

REM ============================================================================
REM  Wgt-Report-Summary - Example 3: scan a folder for reports.
REM
REM  Processes every "Weight_*.htm" file in REPORT_DIR and appends each one into
REM  a single combined CSV.
REM
REM  RECENT_HOURS (time cutoff):
REM     set "RECENT_HOURS=24"  -> process only files edited within the last 24h
REM     set "RECENT_HOURS="    -> process all Weight_*.htm files (no cutoff)
REM
REM  The "recent" branch uses PowerShell for a true hour-based (time) filter.
REM  (The plain batch `forfiles /D -N` command filters by whole days, not hours,
REM  so it is not suitable here.)
REM
REM  SCRIPT_PATH points to run_wgt_summary.py. In this repo the script lives
REM  under src\, so SCRIPT_PATH is "..\src\run_wgt_summary.py". A release build
REM  (build.sh / build.bat) copies this wrapper into dist\ and rewrites
REM  SCRIPT_PATH to "run_wgt_summary.py" (the .py sits next to the wrapper).
REM ============================================================================

REM ---- Most important: the folder to scan for reports. -----------------------
set "REPORT_DIR=."

REM ---- Other settings. ------------------------------------------------------
set "OUTPUT_FILENAME=Weight_Summary.csv"
set "SCRIPT_PATH=..\src\run_wgt_summary.py"

REM Time cutoff in hours. Leave blank (empty) to scan ALL files regardless of
REM how recently they were edited.
set "RECENT_HOURS=24"

REM Resolve the scan folder to an absolute path and show it, so it is clear
REM where the program is scanning for report files.
for %%I in ("%REPORT_DIR%") do set "REPORT_DIR=%%~fI"

REM Start from a clean output file.
if exist "%REPORT_DIR%\%OUTPUT_FILENAME%" del "%REPORT_DIR%\%OUTPUT_FILENAME%"

REM Count how many reports were actually processed, so the final message can tell
REM the difference between "wrote a combined CSV" and "found nothing to write".
set "PROCESSED_COUNT=0"

if defined RECENT_HOURS (
    echo Scanning for Weight_*.htm in %REPORT_DIR% edited within the last %RECENT_HOURS% hours...
    for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%REPORT_DIR%' -Filter 'Weight_*.htm' | Where-Object { $_.LastWriteTime -ge (Get-Date).AddHours(-%RECENT_HOURS%) } | ForEach-Object { $_.FullName }"`) do (
        echo Processing %%F ...
        python "%SCRIPT_PATH%" --file "%%F" --out "%REPORT_DIR%\%OUTPUT_FILENAME%" --options out_append,out_reportfile_stats
        if errorlevel 1 (
            echo FAILED while processing %%F
            pause
            exit /b 1
        )
        set /a PROCESSED_COUNT+=1
    )
) else (
    echo Scanning for Weight_*.htm in %REPORT_DIR% ...
    for %%F in ("%REPORT_DIR%\Weight_*.htm") do if exist "%%F" (
        echo Processing %%F ...
        python "%SCRIPT_PATH%" --file "%%F" --out "%REPORT_DIR%\%OUTPUT_FILENAME%" --options out_append,out_reportfile_stats
        if errorlevel 1 (
            echo FAILED while processing %%F
            pause
            exit /b 1
        )
        set /a PROCESSED_COUNT+=1
    )
)

if !PROCESSED_COUNT! GTR 0 (
    echo Done. Combined summary written to: %REPORT_DIR%\%OUTPUT_FILENAME%
) else (
    echo No Weight_*.htm files found in %REPORT_DIR%; nothing written.
)

endlocal
