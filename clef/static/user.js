var refreshData = document.getElementById('refresh-data');
var playlistsHtml = document.getElementById('playlists');
var playlistCover = document.getElementById('playlist-cover');

function logFailed(req) {
  console.log("Request failed: " + req);
}

function startBackgroundOperation(button, spinner, url, data, success, failed) {
  if (button.classList.contains('disabled')) { return; }
  button.classList.add('disabled');
  spinner.classList.add('busy');
  var xhr = new XMLHttpRequest();
  xhr.open('POST', url);
  if (data != null)
    xhr.setRequestHeader('Content-Type', 'application/json');

  xhr.onload = function() {
    spinner.classList.remove('busy');
    if (xhr.status == 200) {
      if (success != null)
        success(JSON.parse(xhr.responseText))
    } else if (failed != null)
      failed(xhr);

    button.classList.remove('disabled');
  };

  content = data == null ? null : JSON.stringify(data);
  xhr.send(content);
}

function updatePlaylists(playlists) {
  var template = document.getElementById('playlist-item-template').cloneNode(true);
  while (playlistsHtml.firstChild)
    playlistsHtml.removeChild(playlistsHtml.firstChild);

  playlistsHtml.appendChild(template);

  for (var i = 0; i < playlists.length; i++) {
    var li = template.cloneNode();
    li.removeAttribute('id');
    li.classList.remove('hide');
    li.innerText = playlists[i].name + ' (' + playlists[i].track_count + ' tracks)';
    li.dataset.coverUrl = playlists[i].image_url;
    li.addEventListener('mouseenter', mouseEnterPlaylistItem);
    li.addEventListener('mouseleave', mouseLeavePlaylistItem);
    playlistsHtml.appendChild(li);
  }
}

refreshData.addEventListener('click', function(e) {
  var icon = document.getElementById('refresh-data-icon');
  startBackgroundOperation(refreshData, icon, 'refresh', null, updatePlaylists, logFailed);
});

function mouseEnterPlaylistItem(item) {
  if (item.target.dataset.coverUrl != null) {
    playlistCover.setAttribute('src', item.target.dataset.coverUrl);
  }
}

function mouseLeavePlaylistItem(item) {
  // just leave the playlist cover there for now
  //   playlistCover.setAttribute('src', '');
}

playlistItems = playlistsHtml.children;
for (var i = 0; i < playlistItems.length; i++) {
  playlistItems[i].addEventListener('mouseenter', mouseEnterPlaylistItem);
  playlistItems[i].addEventListener('mouseleave', mouseLeavePlaylistItem);
}

var userDisplayName = document.getElementById('user-display-name');
var userSaveButton = document.getElementById('user-save-button');
var savedUserData = {
  displayName: userDisplayName.innerText
};

userDisplayName.addEventListener('keypress', function(e) {
  if (e.which == 13) {
    e.preventDefault();
    e.target.blur();
  }
});

userDisplayName.addEventListener('blur', function(e) {
  if (savedUserData.displayName != userDisplayName.innerText)
    userSaveButton.classList.remove('hide');
  else
    userSaveButton.classList.add('hide');
});

userSaveButton.addEventListener('click', function(e) {
  var icon = document.getElementById('save-user-icon');
  var saveData = {
    displayName: userDisplayName.innerText
  };

  startBackgroundOperation(
    userSaveButton, icon, 'save', saveData,
    function() {
      userSaveButton.classList.add('hide');
      savedUserData.displayName = saveData.displayName;
    },
    function(xhr) {
      showPageWarning("Failed to save your changes: " + xhr.responseText);
    });
});
