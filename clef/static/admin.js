var importButtons = document.querySelectorAll('.import-button');

function checkImportStatus(userId, progress) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', 'import/user/' + e.target.dataset.userId);
  xhr.addEventListener('load', function(loadEvent) {
    if (xhr.status == 202) {
      progress.innerText = xhr.responseText;
      setTimeout(function(){checkImportStatus(userId, progress);}, 1000);
    } else if (xhr.status == 200) {
      progress.innerText = xhr.responseText;
    } else {
      // TODO: ...
    }
  });
  xhr.addEventListener('error', function(errorEvent) ){});
  xhr.send();
}

for (var i = 0; i < importButtons.length; i++) {
  importButtons[i].addEventListener('click', function(e) {
    if (e.target.classList.contains('disabled')) return;
    e.target.classList.add('disabled');
    var row = e.target.parentNode.parentNode;
    var userStatus = row.querySelector('.user-status');
    userStatus.classList.add('hide');
    var progress = row.querySelector('.user-operation');
    progress.classList.remove('hide');
    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'import/user/' + e.target.dataset.userId);
    xhr.addEventListener('load', function(loadEvent) {
      if (xhr.status == 200) {
        progress.innerText = "import starting...";
        setTimeout(function(){checkImportStatus(userId, progress);}, 1000);
      }
    });
    xhr.addEventListener('error', function(errorEvent) ){});

    xhr.send();
  });
}
