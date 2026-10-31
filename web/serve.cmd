@echo off
rem Serves the NEMATICA research site and opens it. Default port 8642; pass another as the first argument.
cd /d "%~dp0"
set PORT=%1
if "%PORT%"=="" set PORT=8642
start "" http://localhost:%PORT%/
where py >nul 2>nul && (py -m http.server %PORT% & goto :eof)
where python >nul 2>nul && (python -m http.server %PORT% & goto :eof)
where npx >nul 2>nul && (npx --yes http-server -p %PORT% -c-1 . & goto :eof)
echo Could not find Python or Node to run a local server. Open index.html directly instead.
pause
