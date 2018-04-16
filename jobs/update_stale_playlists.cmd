::
:: Periodic job to update any playlists marked as stale
::

cd D:\home\site\wwwroot
set FLASK_APP=clef.py
set LOG_NAME=update_stale_playlists.log

D:\home\python364x64\python.exe -m flask update-stale-playlists
