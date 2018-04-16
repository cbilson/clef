::
:: On-demand job to import new users and all their playlists.
::

cd D:\home\site\wwwroot
set FLASK_APP=clef.py

:: Log to a separate file for each new user
set LOG_NAME=Import_%WEBJOBS_COMMAND_ARGUMENTS%.log
D:\home\python364x64\python.exe -m flask import-user-playlists --user-id=%WEBJOBS_COMMAND_ARGUMENTS%
