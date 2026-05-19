@echo off
rem dq.cmd -- wrapper that runs dq.ps1 with execution policy bypassed,
rem so the demo works from any terminal on a stock Windows machine
rem without asking the user to Set-ExecutionPolicy first.
rem
rem Tries PowerShell 7+ (pwsh) first, then falls back to Windows PowerShell 5.1.
where pwsh >nul 2>nul
if %errorlevel% equ 0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0dq.ps1" %*
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dq.ps1" %*
)
