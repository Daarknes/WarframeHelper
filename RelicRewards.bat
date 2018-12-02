@echo off
setlocal
cd src\
set PYTHONPATH=%cd%
python relicrewards\main.py
endlocal

IF not %ERRORLEVEL% == 0 (
	pause
)