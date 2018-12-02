@echo off
setlocal
cd src\
set PYTHONPATH=%cd%
python market\main.py
endlocal

IF not %ERRORLEVEL% == 0 (
	pause
)