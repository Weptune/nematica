@echo off
rem Serves the NEMATICA research site at http://localhost:8000 and opens it.
cd /d "%~dp0"
start "" http://localhost:8000/
where py >nul 2>nul && (py -m http.server 8000 & goto :eof)
where python >nul 2>nul && (python -m http.server 8000 & goto :eof)
where npx >nul 2>nul && (npx --yes http-server -p 8000 -c-1 . & goto :eof)
echo Could not find Python or Node to run a local server. Open index.html directly instead.
pause
