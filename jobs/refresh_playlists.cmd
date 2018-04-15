::
:: Periodic job to check for new user playlist follows/unfollows and freshness
:: of followed playlists.
::

cd D:\home\site\wwwroot
set FLASK_APP=clef.py
set LOG_NAME=Refresh_Playlists.log

D:\home\python364x64\python.exe -m flask refresh-playlists
