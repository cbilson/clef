var refreshData = document.getElementById('refresh-data');
var playlistsHtml = document.getElementById('playlists');
var playlistCover = document.getElementById('playlist-cover');

function logFailed(req) {
  console.log("Request failed: " + req);
}

function startBackgroundOperation(button, feedback, url, data, success, failed, verb) {
  if (button.classList.contains('disabled')) { return; }
  button.classList.add('disabled');
  feedback.classList.add('busy');
  var xhr = new XMLHttpRequest();
  verb = verb == null ? 'POST' : verb;
  xhr.open(verb, url);
  if (data != null)
    xhr.setRequestHeader('Content-Type', 'application/json');

  xhr.onload = function() {
    feedback.classList.remove('busy');
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

function showGenres(playlistDetails) {
  var genreCloud = document.getElementById('genre-cloud');
  while (genreCloud.firstChild)
    genreCloud.removeChild(genreCloud.firstChild);

  var maxScore = 0;
  for (var genre in playlistDetails.genres)
    if (playlistDetails.genres[genre] > maxScore)
      maxScore = playlistDetails.genres[genre]

  console.log('max genre score: ' + maxScore);

  for (var genre in playlistDetails.genres) {
    var genreSpan = document.createElement('span');
    genreSpan.innerText = genre;
    var score = playlistDetails.genres[genre];
    var pct = score / maxScore;
    console.log('score for ' + genre + ' = ' + score + ' (pct. ' + pct + ')');
    genreSpan.style.fontSize = (100 * pct) + '%';
    genreSpan.style.margin = '3px';
    genreCloud.appendChild(genreSpan);
  }
}

function showPlaylistAttributes(playlistDetails) {
  document.getElementById('danceability-value').innerText = playlistDetails.danceability.toFixed(2);
  document.getElementById('energy-value').innerText = playlistDetails.energy.toFixed(2);
  document.getElementById('loudness-value').innerText = playlistDetails.loudness.toFixed(2);
  document.getElementById('tempo-value').innerText = playlistDetails.tempo.toFixed(0);
  document.getElementById('acousticness-value').innerText = playlistDetails.acousticness.toFixed(2);
  document.getElementById('instrumentalness-value').innerText = playlistDetails.instrumentalness.toFixed(2);
  document.getElementById('liveness-value').innerText = playlistDetails.liveness.toFixed(2);
  document.getElementById('speechiness-value').innerText = playlistDetails.speechiness.toFixed(2);
  document.getElementById('valence-value').innerText = playlistDetails.valence.toFixed(2);
}

function clickPlaylist(item) {
  var url = 'playlist/' + item.target.dataset.id + '/details';
  var icon = document.getElementById('playlist-loading');
  icon.classList.remove('hide');
  startBackgroundOperation(
    userSaveButton, icon, url, null,
    function(playlistDetails) {
      icon.classList.add('hide');
      var autoPlay = document.getElementById('auto-play');
      if (autoPlay.value) {
        var nowPlayling = document.getElementById('now-playing');
        nowPlayling.classList.remove('hide');

        var nowPlayingName = document.getElementById('now-playing-name');
        nowPlayingName.innerText = playlistDetails.name;

        showGenres(playlistDetails);
        showPlaylistAttributes(playlistDetails);
      }
    },
    function(xhr) {
      icon.classList.add('hide');
      showPageWarning("Failed to load playlist.");
    }, 'GET');
}

playlistItems = playlistsHtml.children;
for (var i = 0; i < playlistItems.length; i++) {
  playlistItems[i].addEventListener('mouseenter', mouseEnterPlaylistItem);
  playlistItems[i].addEventListener('mouseleave', mouseLeavePlaylistItem);
  playlistItems[i].addEventListener('click', clickPlaylist);
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
