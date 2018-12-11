@echo off
setlocal
cd src\
set PYTHONPATH=%cd%
py -3 relicrewards\main.py
endlocal

IF not %ERRORLEVEL% == 0 (
	pause
)