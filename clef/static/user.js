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

var currentSongs = null;
var player = document.getElementById('audio-preview-controls');
var autoPlaySwitch = document.getElementById('auto-play');
var nowPlaying = document.getElementById('now-playing');
function mouseEnterPlaylistItem(item) {
  if (item.target.dataset.coverUrl != null) {
    playlistCover.setAttribute('src', item.target.dataset.coverUrl);
  }
}

function mouseLeavePlaylistItem(item) {
  // flip back to the the playling playlist if there is one.
  if (nowPlaying.dataset.coverUrl)
    playlistCover.setAttribute('src', nowPlaying.dataset.coverUrl);
}

function showGenres(playlistDetails) {
  var genreCloud = document.getElementById('genre-cloud');
  while (genreCloud.firstChild)
    genreCloud.removeChild(genreCloud.firstChild);

  var maxScore = 0;
  for (var genre in playlistDetails.genres)
    if (playlistDetails.genres[genre] > maxScore)
      maxScore = playlistDetails.genres[genre]

  for (var genre in playlistDetails.genres) {
    var genreSpan = document.createElement('span');
    genreSpan.innerText = genre;
    var score = playlistDetails.genres[genre];
    var pct = score / maxScore;
    genreSpan.style.fontSize = (100 * pct) + '%';
    genreSpan.style.margin = '3px';
    genreCloud.appendChild(genreSpan);
  }
}

function setNumericText(id, precision, val) {
  if (val == null)
    document.getElementById(id).innerText = '';
  else
    document.getElementById(id).innerText = val.toFixed(precision);
}

function showPlaylistAttributes(playlistDetails) {
  setNumericText('danceability-value', 2, playlistDetails.danceability);
  setNumericText('energy-value', 2, playlistDetails.energy);
  setNumericText('loudness-value', 2, playlistDetails.loudness);
  setNumericText('tempo-value', 0, playlistDetails.tempo);
  setNumericText('acousticness-value', 2, playlistDetails.acousticness);
  setNumericText('instrumentalness-value', 2, playlistDetails.instrumentalness);
  setNumericText('liveness-value', 2, playlistDetails.liveness);
  setNumericText('speechiness-value', 2, playlistDetails.speechiness);
  setNumericText('valence-value', 2, playlistDetails.valence);
}

var switchSampleTimeout = null;
function stopSamplePlayback() {
  if (switchSampleTimeout != null)
    clearTimeout(switchSampleTimeout);

  player.pause();
}

autoPlaySwitch.addEventListener('click', function() {
  if (!autoPlaySwitch.checked)
    stopSamplePlayback();
});

function playNextSample() {
  if (currentSongs == null)
    return;

  if (!autoPlaySwitch.checked)
    return;

  var source = document.getElementById('audio-preview-source');
  source.src = currentSongs.shift();
  currentSongs.push(source.src);

  player.load();
  player.play();
  switchSampleTimeout = setTimeout(playNextSample, 5000);
}

function playSampleTracks(playlistDetails) {
  stopSamplePlayback();
  currentSongs = playlistDetails.previews;
  playNextSample();
}

function clickPlaylist(item) {
  nowPlaying.dataset.coverUrl = item.target.dataset.coverUrl;
  nowPlaying.dataset.playlistId = item.target.dataset.id;
  document.getElementById('recommend-panel').classList.remove('hide');
  var url = 'playlist/' + item.target.dataset.id + '/details';
  var icon = document.getElementById('playlist-loading');
  icon.classList.remove('hide');
  startBackgroundOperation(
    userSaveButton, icon, url, null,
    function(playlistDetails) {
      icon.classList.add('hide');
      var nowPlayingName = document.getElementById('now-playing-name');
      nowPlayingName.innerText = playlistDetails.name;

      showGenres(playlistDetails);
      showPlaylistAttributes(playlistDetails);
      playSampleTracks(playlistDetails);
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

recommendButton = document.getElementById('recommendButton');
recommendButton.addEventListener('click', function() {
  if (nowPlaying.dataset.playlistId == null)
    return;

  recommendButton.classList.add('disabled');
  recommended = document.getElementById('recommended');

  recommended.classList.add('hide');

  var xhr = new XMLHttpRequest();
  xhr.open('GET', 'playlist/' + nowPlaying.dataset.playlistId + '/recommend');
  xhr.onload = function() {
    recommendButton.classList.remove('disabled');

    if (xhr.status == 200) {
      recommended.classList.remove('hide');
      recs = JSON.parse(xhr.responseText);
      var track = document.getElementById('recommended-track');
      track.innerText = recs.name;
      track.href = recs.external_urls.spotify;

      var artist = document.getElementById('recommended-artist');
      artist.innerText = recs.artists[0].name;
      artist.href = recs.artists[0].external_urls.spotify;
    }
  };

  xhr.send();
});
