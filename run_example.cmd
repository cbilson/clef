@echo off

echo Copy this to run.cmd (ignored in .gitignore), put in secrets
echo and use this to start the application locally.

set LOG_PATH=%~dp0

set MYSQL_DATABASE_HOST=clefdb.mysql.database.azure.com
set MYSQL_DATABASE_DB=clef
set MYSQL_DATABASE_USER=***
set MYSQL_DATABASE_PASSWORD=***

set SPOTIFY_CLIENT_ID=***
set SPOTIFY_CLIENT_SECRET=***

set DEBUG=1
set FLASK_DEBUG=1

set FLASK_APP=clef.py

python -m flask run
