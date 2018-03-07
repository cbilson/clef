@echo off

echo Copy this to run.cmd (ignored in .gitignore), put in secrets
echo and use this to start the application locally.

set DB_HOST=clefdb.mysql.database.azure.com
set DB_NAME=clef
set DB_USER=***
set DB_PASSWORD=***
set SPOTIFY_CLIENT_ID=***
set SPOTIFY_CLIENT_SECRET=***
set DEBUG=1

python clef.py
