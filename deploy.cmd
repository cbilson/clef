@if "%SCM_TRACE_LEVEL%" NEQ "4" @echo off

:: Verify node.js installed
where node 2>nul >nul
IF %ERRORLEVEL% NEQ 0 (
  echo Missing node.js executable, please install node.js, if already installed make sure it can be reached from current environment.
  goto error
)

setlocal enabledelayedexpansion

SET ARTIFACTS=%~dp0%..\artifacts

IF NOT DEFINED DEPLOYMENT_SOURCE (
  SET DEPLOYMENT_SOURCE=%~dp0%.
)

IF NOT DEFINED DEPLOYMENT_TARGET (
  SET DEPLOYMENT_TARGET=%ARTIFACTS%\wwwroot
)

IF NOT DEFINED KUDU_SYNC_CMD (
  :: Install kudu sync
  echo Installing Kudu Sync
  call npm install kudusync -g --silent
  IF !ERRORLEVEL! NEQ 0 goto error

  :: Locally just running "kuduSync" would also work
  SET KUDU_SYNC_CMD=%appdata%\npm\kuduSync.cmd
)

echo Determing Python environment
SET PYTHON_RUNTIME=python-3.6
SET PYTHON_VER=3.6
SET PYTHON_HOME=D:\home\python364x64
SET PYTHON_SCRIPTS=D:\home\python364x64\scripts
SET PYTHON_EXE=%PYTHON_HOME%\python.exe
echo PYTHON_EXE = %PYTHON_EXE%

echo Updating path with python home
SET PATH=%PYTHON_HOME%;%PYTHON_SCRIPTS%;%PATH%

echo Executing KudoSync
IF /I "%IN_PLACE_DEPLOYMENT%" NEQ "1" (
  call :ExecuteCmd "%KUDU_SYNC_CMD%" -v 50 -f "%DEPLOYMENT_SOURCE%" -t "%DEPLOYMENT_TARGET%" -n "%NEXT_MANIFEST_PATH%" -p "%PREVIOUS_MANIFEST_PATH%" -i ".git;.hg;.deployment;deploy.cmd"
  IF !ERRORLEVEL! NEQ 0 goto error
)

echo Ensuring application log path exists
set APP_LOGS=D:\home\LogFiles\Application
if not exist %APP_LOGS% (
   echo Creating application log folder
   mkdir %APP_LOGS%
)

pushd "%DEPLOYMENT_TARGET%"

echo Updating pip
%PYTHON_EXE% -m pip install --upgrade pip

echo Installing python packages
%PYTHON_EXE% -m pip install -r requirements.txt
IF !ERRORLEVEL! NEQ 0 goto error

set FLASK=%PYTHON_SCRIPTS%\flask.exe

echo Runnig Pre-flight check
set FLASK_APP=clef.py
set HTTP_PLATFORM_PORT=9000
%FLASK% preflight-check

popd

::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
goto end

:: Execute command routine that will echo out when error
:ExecuteCmd
setlocal
set _CMD_=%*
call %_CMD_%
if "%ERRORLEVEL%" NEQ "0" echo Failed exitCode=%ERRORLEVEL%, command=%_CMD_%
exit /b %ERRORLEVEL%

:error
endlocal
echo An error has occurred during web site deployment.
call :exitSetErrorLevel
call :exitFromFunction 2>nul

:exitSetErrorLevel
exit /b 1

:exitFromFunction
()

:end
endlocal
echo Finished successfully.
