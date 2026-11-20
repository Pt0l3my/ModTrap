@echo off
rem Starts ModTrap: a page in your browser, served on this PC only. Needs Python 3.10 or newer.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m modtrap %*
) else (
  python -m modtrap %*
)
if errorlevel 1 pause
