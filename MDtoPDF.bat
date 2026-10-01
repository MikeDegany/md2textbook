@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw md2pdf.py %*
) else (
    python md2pdf.py %*
)
