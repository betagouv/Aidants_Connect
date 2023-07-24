"use strict";

import {BaseController} from "./base-controller.js"

(function () {
    const SEARCH_EVENT_NAME = "search:search"

    // We create the collator once because it is a costly operation
    const collator = new Intl.Collator(navigator.language, {
        usage: "search",
        sensitivity: "base",
    })

    // Inspired by https://github.com/idmadj/locale-includes/blob/master/src/index.js
    function localeIncludes (haystack, needle) {
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

    class SearchController extends BaseController {
        initialize () {
            this.itemTargets.forEach(item => {
                item.setAttribute("data-controller", "search-item");
                item.setAttribute("data-search-item-target", "item");
            });
        }

        connect () {
            this.searchBarTargets.forEach(this.showElement);
            this.searchTokenValue = this.searchInputTarget.value;
        }

        search (evt) {
            this.searchTokenValue = evt.target.value.trim();
        }

        searchTokenValueChanged (value) {
            const event = new CustomEvent(SEARCH_EVENT_NAME, {detail: {term: value.trim()}});
            this.element.dispatchEvent(event);
        }

        static targets = [
            "searchBar",
            "item",
            "searchInput",
        ];

        static values = {
            searchToken: String
        }
    }

    class SearchItemController extends BaseController {
        initialize () {
            this.searchTerms = JSON.parse(this.itemTarget.dataset.searchTerms);
        }

        connect () {
            this.boundFilter = this.filter.bind(this);
            document.querySelector("[data-controller='search']").addEventListener(
                SEARCH_EVENT_NAME, this.boundFilter
            );
        }

        filter (event) {
            const searchTerm = event.detail.term;

            if (searchTerm.length === 0) {
                // Empty searchbar case
                this.showElement(this.itemTarget);
                return;
            }

            const hasMatchingTerms = this.searchTerms.some(function (term) {
                return localeIncludes(term, searchTerm);
            });

            this.mutateVisibility(hasMatchingTerms, this.itemTarget);
        }

        disconnect () {
            document.querySelector("[data-controller='search']").removeEventListener(
                SEARCH_EVENT_NAME, this.boundFilter
            );
        }

        static targets = ["item"]
    }

    function init () {
        const application = Stimulus.Application.start();
        application.register("search", SearchController);
        application.register("search-item", SearchItemController);
    }

    window.addEventListener("load", init);
})();
