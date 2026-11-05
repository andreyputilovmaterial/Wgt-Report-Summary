@ECHO OFF
setlocal
cd /d "%~dp0"

REM ============================================================================
REM  Build the release folder (dist\) from src\ and scripts\.
REM
REM  Copies run_wgt_summary.py and every run_*.bat / run_*.sh wrapper into
REM  dist\, rewriting each wrapper's SCRIPT_PATH so the .py is expected in the
REM  SAME folder as the wrapper (the repo's "..\src\" / "../src/" prefix is
REM  stripped). .bat wrappers are written with CRLF line endings.
REM ============================================================================

if exist dist rmdir /s /q dist
mkdir dist

copy /y "src\run_wgt_summary.py" "dist\" >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $dist='dist'; $files = Get-ChildItem -LiteralPath 'scripts' -File; foreach ($f in $files) { if ($f.Name -like 'run_*.bat' -or $f.Name -like 'run_*.sh') { $lines = foreach ($line in (Get-Content -LiteralPath $f.FullName)) { $line.Replace('SCRIPT_PATH=..\src\','SCRIPT_PATH=').Replace('SCRIPT_PATH=../src/','SCRIPT_PATH=') }; if ($f.Name -like 'run_*.bat') { Set-Content -Encoding ASCII -LiteralPath (Join-Path $dist $f.Name) -Value $lines } else { Set-Content -NoNewline -Encoding ASCII -LiteralPath (Join-Path $dist $f.Name) -Value ($lines -join [char]10) } } }"

echo Built dist\
