"use strict";

$(function () {
    const users = JSON.parse(document.querySelector("#usagers_list").textContent);
    $("#filter-input").autocomplete({
        source: users,
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
