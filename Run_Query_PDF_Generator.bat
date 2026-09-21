@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py Query_PDF_Generator.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python Query_PDF_Generator.py
    goto :end
)

echo Python was not found on this computer.
echo.
echo Please install Python 3.x and then run:
echo     pip install -r requirements.txt
echo.
pause

:end
endlocal
