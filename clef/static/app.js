M.Dropdown.init(document.querySelector('.dropdown-trigger'));

searchTextOptions = {minLength: 3};
search = M.Autocomplete.init(
  document.getElementById('search-text'),
  searchTextOptions);

var pendingSearch = null;
search.el.addEventListener('input', function(e) {
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

      search.updateData(data);
      pendingSearch = null;
    }
  }

  pendingSearch.send();
});
