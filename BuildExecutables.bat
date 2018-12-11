@echo off
setlocal
REM Delete old installations
rmdir /s /q Executables
rmdir /s /q dist

REM create the executables folder
md .\Executables\

REM Build the market helper.
pyinstaller ./src/market/main.py

REM Copy the needed files to the correct place
xcopy /q res dist\res\
xcopy /q config dist\config\
xcopy /q BuildEssentials\MarketHelper.bat dist\

REM Delete the downloaded market prices file
del /q dist\res\market_prices.json

REM Move the folder to its final position and rename it
move dist Executables
rename Executables\dist MarketHelper

rmdir /s /q build

REM ====================0

REM Build the relic helper.
pyinstaller ./src/relicrewards/main.py

REM Copy the needed files to the correct place
xcopy /q res dist\res\
xcopy /q config dist\config\
xcopy /q BuildEssentials\RelicHelper.bat dist\

REM Delete the downloaded market prices file
del /q dist\res\market_prices.json

REM Move the folder to its final position and rename it
move dist Executables
rename Executables\dist RelicHelper

rmdir /s /q build