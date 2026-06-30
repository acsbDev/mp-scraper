@echo off
cd /d "%~dp0"

echo Installing pipenv...
py -m pip install --user pipenv

echo Installing project dependencies...
pipenv install

echo.
echo Installation completed.
pause