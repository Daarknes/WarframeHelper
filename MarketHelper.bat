@echo off
setlocal
cd src\
set PYTHONPATH=%cd%
python market\main.py
endlocal
pause