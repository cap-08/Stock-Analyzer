@echo off
REM Launches the Flask server in the background and opens the dashboard in your browser.
cd /d "%~dp0"

REM Start the Flask server in a separate minimized window
start "NIFTY 50 Dashboard Server" /min python app.py

REM Give the server a couple seconds to boot up
timeout /t 3 /nobreak >nul

REM Open the site in your default browser
start "" http://127.0.0.1:5000

echo.
echo The dashboard should now be open in your browser.
echo (A minimized server window is running in the background - closing it will stop the site.)
