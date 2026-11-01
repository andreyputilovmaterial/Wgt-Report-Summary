@ECHO OFF

REM ============================================================================
REM  Wgt-Report-Summary - Example 3: scan the current folder for reports.
REM
REM  Processes every "Weight_*.htm" file and appends each one into a single
REM  combined CSV.
REM
REM  ONLY_RECENT toggle:
REM     set "ONLY_RECENT=1"  -> process only files edited within the last 24h
REM     set "ONLY_RECENT=0"  -> process all Weight_*.htm files
REM
REM  The "recent" branch uses PowerShell for a true 24-hour (time-based) filter.
REM  (The plain batch `forfiles /D -N` command filters by whole days, not hours,
REM  so it is not suitable here.)
REM
REM  In a release, run_wgt_summary.py sits in the same folder as this .bat, so
REM  SCRIPT can simply be "run_wgt_summary.py". In this repo the script lives
REM  under src\, hence the "..\src\" prefix. Update SCRIPT to match your layout.
REM ============================================================================

set "SCRIPT=..\src\run_wgt_summary.py"
set "OUT=Weight_Summary.csv"
set "ONLY_RECENT=0"

REM Start from a clean output file.
if exist "%OUT%" del "%OUT%"

if "%ONLY_RECENT%"=="1" (
    echo Scanning Weight_*.htm edited within the last 24 hours...
    for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-ChildItem -Filter 'Weight_*.htm' | Where-Object { $_.LastWriteTime -ge (Get-Date).AddHours(-24) } | ForEach-Object { $_.FullName }"`) do (
        echo Processing %%F ...
        python "%SCRIPT%" --file "%%F" --out "%OUT%" --options out_append,out_reportfile_stats
        if errorlevel 1 (
            echo ERROR: Failure while processing %%F
            pause
            exit /b 1
        )
    )
) else (
    echo Scanning all Weight_*.htm files...
    for %%F in (Weight_*.htm) do (
        echo Processing %%F ...
        python "%SCRIPT%" --file "%%F" --out "%OUT%" --options out_append,out_reportfile_stats
        if errorlevel 1 (
            echo ERROR: Failure while processing %%F
            pause
            exit /b 1
        )
    )
)

echo Done. Combined summary written to: %OUT%
