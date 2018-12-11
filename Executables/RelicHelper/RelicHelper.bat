@echo off
setlocal
main\main.exe
endlocal

IF not %ERRORLEVEL% == 0 (
	pause
)