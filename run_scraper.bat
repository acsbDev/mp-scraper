@echo off
cd /d "%~dp0"

echo Running MercadoPublico scraper...
pipenv run python main.py

echo.
echo Scraper finished.
pause