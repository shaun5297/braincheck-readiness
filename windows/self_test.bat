@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
"%PROJECT_ROOT%\.venv-supported\Scripts\python.exe" -m unittest discover -s "%PROJECT_ROOT%\tests" -v || exit /b 1
"%PROJECT_ROOT%\.venv-supported\Scripts\braincheck-self-test.exe" || exit /b 1
