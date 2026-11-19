@echo off
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0spustit-na-mobile.ps1"
if errorlevel 1 pause
