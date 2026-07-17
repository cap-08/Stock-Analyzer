@echo off
REM Stops the Flask server started by start_app.bat
echo Stopping NIFTY 50 Dashboard server...
taskkill /F /FI "WINDOWTITLE eq NIFTY 50 Dashboard Server*" >nul 2>&1
echo Done.
pause
