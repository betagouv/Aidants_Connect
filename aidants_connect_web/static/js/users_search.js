"use strict";

(function () {
    const SEARCH_EVENT_NAME = "search:search"

    // We create the collator once because it is a costly operation
    const collator = new Intl.Collator(navigator.language, {
        usage: "search",
        sensitivity: "base",
    })

    // Inspired by https://github.com/idmadj/locale-includes/blob/master/src/index.js
    function localeIncludes(haystack, needle) {
        const haystackLength = haystack.length;
        const needleLength = needle.length;
        const lengthDiff = haystackLength - needleLength;

        for (var i = 0; i <= lengthDiff; i++) {
            const subHaystack = haystack.substring(i, i + needleLength);
            if (collator.compare(subHaystack, needle) === 0) {
                return true
            }
        }
        return false
    }

    /*
     * This was made with Stimulus framework
     * https://stimulus.hotwired.dev
     */
    const SearchController = Object.extendClass(Stimulus.Controller);
    Object.assign(SearchController.prototype, {
        "initialize": function initialize() {
            this.itemTargets.forEach(function (item) {
                item.setAttribute("data-controller", "search-item");
                item.setAttribute("data-search-item-target", "item");
            });
        },

        "connect": function connect() {
            this.searchBarTargets.forEach(function (searchBar) {
                searchBar.removeAttribute("hidden");
            });
        },

        "search": function search(evt) {
            const event = new CustomEvent(SEARCH_EVENT_NAME, {detail: {term: evt.target.value.trim()}});
            this.element.dispatchEvent(event);
        },
    });

    SearchController.targets = ["searchBar", "item"];

    const SearchItemController = Object.extendClass(Stimulus.Controller);
    Object.assign(SearchItemController.prototype, {
        "initialize": function initialize() {
            this.searchTerms = JSON.parse(this.itemTarget.dataset.searchTerms);
        },

        "connect": function connect() {
            this.boundFilter = this.filter.bind(this);
            document.querySelector("[data-controller='search']").addEventListener(SEARCH_EVENT_NAME, this.boundFilter);
        },

        "filter": function filter(event) {
            const searchTerm = event.detail.term;

            if (searchTerm.length === 0) {
                // Empty searchbar
                this.itemTarget.removeAttribute("hidden");
                return;
            }

            const hasMatchingTerms = this.searchTerms.some(function (term) {
                return localeIncludes(term, searchTerm);
            });

            if (hasMatchingTerms) {
                this.itemTarget.removeAttribute("hidden");
            } else {
                this.itemTarget.setAttribute("hidden", "hidden");
            }
        },

        "disconnect": function disconnect() {
            document.querySelector("[data-controller='search']").removeEventListener(SEARCH_EVENT_NAME, this.boundFilter);
        },
    });

    SearchItemController.targets = ["item"];

    function init() {
        const application = Stimulus.Application.start();
        application.register("search", SearchController);
        application.register("search-item", SearchItemController);
    }

    window.addEventListener("load", init);
})();
