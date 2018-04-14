var importButtons = document.querySelectorAll('.import-button');

function checkImportStatus(importButton, progress, userStatus) {
  var xhr = new XMLHttpRequest();
  var jobId = progress.dataset.jobId;
  var url = 'import/job/' + jobId;
  xhr.open('GET', url);
  xhr.addEventListener('load', function(loadEvent) {
    if (xhr.status == 200) {
      job = JSON.parse(xhr.responseText);
      if (job.status == 'Success') {
        progress.classList.add('hide');
        importButton.classList.remove('disabled');
        userStatus.innerText = 'Import complete!';
        importButton.classList.add('hide');
      } else if (job.status == 'Failed') {
        showPageWarning("Import job failed.");
        progress.classList.add('hide');
        importButton.classList.remove('disabled');
        userStatus.innerText = 'Failed';
      } else {
        userStatus.innerText = job.status;
        setTimeout(function(){checkImportStatus(importButton, progress, userStatus);}, 3000);
      }
    } else {
      // TODO: Feedback of some kind
      userStatus.innerText = 'Something is up...';
      setTimeout(function(){checkImportStatus(importButton, progress, userStatus);}, 3000);
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
    var progress = row.querySelector('.user-operation');
    progress.classList.remove('hide');
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'import/user/' + e.target.dataset.userId);
    xhr.addEventListener('load', function(loadEvent) {
      if (xhr.status == 202) {
        var res = JSON.parse(xhr.responseText);
        progress.dataset.jobId = res.jobId;
        userStatus.innerText = res.status;
        setTimeout(function(){checkImportStatus(e.target, progress, userStatus);}, 3000);
      }
    });
    xhr.addEventListener('error', showPageWarning);

    xhr.send();
  });
}
