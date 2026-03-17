@ECHO OFF


python run_wgt_summary.py --file "Weight_Report.htm"
if %ERRORLEVEL% NEQ 0 ( echo ERROR: Failure && pause && exit /b %errorlevel% )


