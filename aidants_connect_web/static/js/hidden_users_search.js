$(() => {
  const collator = new Intl.Collator(navigator.language, {
    usage: "search",
    sensitivity: "base",
  });

  // Inspired by https://github.com/idmadj/locale-includes/blob/master/src/index.js
  function localeIncludes(haystack, needle) {
    const haystackLength = haystack.length;
    const needleLength = needle.length;
    const lengthDiff = haystackLength - needleLength;

    for (let i = 0; i <= lengthDiff; i++) {
      const subHaystack = haystack.substring(i, i + needleLength);
      if (collator.compare(subHaystack, needle) === 0) {
        return true;
      }
    }
    return false;
  }

  const users = JSON.parse(document.querySelector("#usagers_list").textContent);
  $("#anonymous-filter-input")
    .autocomplete({
      source: (request, response) => {
        const results = users.filter((item) =>
          localeIncludes(item.label, request.term),
        );

        response(results);
      },
      minLength: 3,
      select: (event, ui) => {
        $("#anonymous-filter-input").val(ui.item.label);
        $("#anonymous-filter-input-id").val(ui.item.value);
        return false;
      },
      appendTo: $("#autocomplete"),
    })
    .data("ui-autocomplete")._renderItem = (ul, item) =>
    $("<li class=ui-menu-item-wrapper>")
      .attr("data-value", item.value)
      .append(item.label)
      .appendTo(ul);
});
