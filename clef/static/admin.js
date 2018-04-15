var importButtons = document.querySelectorAll('.import-button');
const POLLING_FREQ = 1000;

function checkImportStatus(userId, importButton, progress, userStatus, row) {
  var xhr = new XMLHttpRequest();
  var jobId = progress.dataset.jobId;
  var url = 'import/user/' + userId + '/job/' + jobId;
  var resultsButton = row.querySelector('.results-button');
  xhr.open('GET', url);
  xhr.addEventListener('load', function(loadEvent) {
    if (xhr.status == 200) {
      job = JSON.parse(xhr.responseText);
      if (job.status == 'Success') {
        progress.classList.add('hide');
        importButton.classList.remove('disabled');
        importButton.classList.add('hide');
        resultsButton.href = 'import/job/' + jobId + '/results';
        row.querySelector('.playlist-count').innerText = job.userInfo.playlistCount;
        userStatus.innerText = job.userInfo.status;
        resultsButton.classList.remove('hide');
      } else if (job.status == 'Failed') {
        showPageWarning("Import job failed.");
        progress.classList.add('hide');
        importButton.classList.remove('disabled');
        userStatus.innerText = 'Failed';
      } else {
        userStatus.innerText = job.status + ': ' + job.duration.substring(0, 8);
        row.querySelector('.user-operation-log').href =
          'https://clef2.scm.azurewebsites.net/vfs/data/jobs/triggered/import-user-playlists/'
          + jobId + '/output_log.txt';
        setTimeout(function(){
          checkImportStatus(userId, importButton, progress, userStatus, row);
        }, POLLING_FREQ);
      }
    } else {
      // TODO: Feedback of some kind
      userStatus.innerText = 'Something is up...';
      setTimeout(function(){
        checkImportStatus(userId, importButton, progress, userStatus, row);
      }, POLLING_FREQ);
    }
  });
  xhr.addEventListener('error', showPageWarning);
  xhr.send();
}

for (var i = 0; i < importButtons.length; i++) {
  importButtons[i].addEventListener('click', function(e) {
    if (e.target.classList.contains('disabled')) return;
    e.target.classList.add('disabled');
    var row = e.target.parentNode.parentNode;
    var userStatus = row.querySelector('.user-status');
    var progress = row.querySelector('.user-operation-progress');
    progress.classList.remove('hide');
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'import/user/' + e.target.dataset.userId);
    xhr.addEventListener('load', function(loadEvent) {
      if (xhr.status == 202) {
        var res = JSON.parse(xhr.responseText);
        progress.dataset.jobId = res.jobId;
        userStatus.innerText = res.status;
        setTimeout(function () {
          checkImportStatus(e.target.dataset.userId, e.target, progress, userStatus, row);
        }, POLLING_FREQ);
      }
    });
    xhr.addEventListener('error', showPageWarning);

    xhr.send();
  });
}
