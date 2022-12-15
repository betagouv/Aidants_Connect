"use strict";

$(function () {
    const collator = new Intl.Collator(navigator.language, {
        usage: "search",
        sensitivity: "base",
    })

    // Inspired by https://github.com/idmadj/locale-includes/blob/master/src/index.js
    function localeIncludes(haystack, needle) {
        const haystackLength = haystack.length
        const needleLength = needle.length
        const lengthDiff = haystackLength - needleLength

        for (var i = 0; i <= lengthDiff; i++) {
            const subHaystack = haystack.substring(i, i + needleLength)
            if (collator.compare(subHaystack, needle) === 0) {
                return true
            }
        }
        return false
    }

    const users = JSON.parse(document.querySelector("#usagers_list").textContent);
    $("#filter-input").autocomplete({
        source: function (request, response) {
            const results = users.filter(function(item) {
                return localeIncludes(item.label, request.term);
            });

            response(results);
        },
        minLength: 3,
        focus: function (event, ui) {
            $("#filter-input").val(ui.item.label);
            return false;
        },
        select: function (event, ui) {
            $("#filter-input").val(ui.item.label);
            $("#filter-input-id").val(ui.item.value);
            return false;
        },
        appendTo: $("#autocomplete"),
    })
        .data("ui-autocomplete")._renderItem = function (ul, item) {
        return $("<li class=ui-menu-item-wrapper>")
            .attr("data-value", item.value)
            .append(item.label)
            .appendTo(ul);
    };
});
