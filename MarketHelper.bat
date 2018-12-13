@echo off
setlocal
cd src\
set PYTHONPATH=%cd%

WHERE py >nul 2>nul
IF %ERRORLEVEL% == 0 (
	py -3 market\main.py
) ELSE (
    python market\main.py
)
endlocal

IF not %ERRORLEVEL% == 0 (
	pause
)