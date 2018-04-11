M.Dropdown.init(document.querySelector('.dropdown-trigger'));

searchTextOptions = {minLength: 3};
search = M.Autocomplete.init(document.getElementById('search-text'), searchTextOptions);
search.el.addEventListener('input', function(e) {
  if (e.target.value.length < 3) {
    return;
  }

  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/search?term=' + e.target.value);
  xhr.onload = function() {
    console.log(xhr.responseText);
    if (xhr.status == 200) {
      data = {};
      var results = JSON.parse(xhr.responseText);
      for (var i = 0; i < results.length; i++) {
        data[results[i].name + ' (' + results[i].type + ')'] = null;
      }

      search.updateData(data);
    }
  }

  xhr.send();
});
