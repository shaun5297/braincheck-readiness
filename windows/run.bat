@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
"%PROJECT_ROOT%\.venv-supported\Scripts\braincheck.exe" %*
