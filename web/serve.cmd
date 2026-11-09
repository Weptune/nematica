@echo off
rem Serves the NEMATICA research site with the brain-likeness test at /test/, and opens it.
rem Default port 8642; pass another as the first argument.
cd /d "%~dp0.."
set PORT=%1
if "%PORT%"=="" set PORT=8642
set PY=
where py >nul 2>nul && set PY=py
if not defined PY (where python >nul 2>nul && set PY=python)
if defined PY (
  %PY% -c "import fastapi, uvicorn, scipy, onnxruntime" >nul 2>nul && (
    start "" http://localhost:%PORT%/
    %PY% -m nematica.brainlike.web.site %PORT%
    goto :eof
  )
  echo The brain-likeness test needs a few packages. Install them once with:
  echo   %PY% -m pip install -r deploy\brainlike\requirements.txt
  echo Serving the research site without the test for now.
  start "" http://localhost:%PORT%/
  %PY% -m http.server %PORT% -d web
  goto :eof
)
where npx >nul 2>nul && (start "" http://localhost:%PORT%/ & npx --yes http-server web -p %PORT% -c-1 & goto :eof)
echo Could not find Python or Node to run a local server. Open web\index.html directly instead.
pause
