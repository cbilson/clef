M.AutoInit();

var pendingSearch = null;
var searchText = document.getElementById('search-text');
searchText.addEventListener('input', function(e) {
  if (e.target.value.length < 3)
    return;

  if (pendingSearch != null)
    pendingSearch.abort();

  pendingSearch = new XMLHttpRequest();
  pendingSearch.open('GET', '/search?term=' + e.target.value);
  pendingSearch.onload = function() {
    if (pendingSearch.status == 200) {
      data = {};
      var results = JSON.parse(pendingSearch.responseText);
      for (var i = 0; i < results.length; i++)
        data[results[i].name + ' (' + results[i].type + ')'] = null;

      M.Autocomplete.getInstance(searchText).updateData(data);
      pendingSearch = null;
    }
  }

  pendingSearch.send();
});


function showPageWarning(msg) {
  icon = document.getElementById('page-warning');

  // "restart" the animation
  icon.classList.remove('fade-alert');
  void icon.offsetWidth;
  icon.classList.add('fade-alert');

  // set the warning tooltip and show a toast notification.
  icon.dataset.tooltip = msg;
  M.toast({html: msg});
}
