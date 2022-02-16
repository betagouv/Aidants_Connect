"use strict";

(function () {
    /** Logic for correctly extending a class in ES5 */
    function extend(superClass) {
        const _constructor = function () {
            Object.getPrototypeOf(_constructor).apply(this, arguments);
        }

        _constructor.prototype = Object.create(superClass.prototype, {
            constructor: {
                value: _constructor,
                writable: true,
                configurable: true
            }
        });
        Object.setPrototypeOf(_constructor, superClass);

        return _constructor;
    }

    // We create the collator once because it is a costly operation
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

    /*
     * This was made with Stimulus framework
     * https://stimulus.hotwired.dev
     */
    const SearchController = extend(Stimulus.Controller)
    SearchController.prototype.connect = function () {
        this.searchBarTargets.forEach(function (searchBar) {
            searchBar.removeAttribute("hidden")
        })
    }

    SearchController.prototype.search = function (evt) {
        const self = this
        const searchQuery = evt.target.value.trim()
        this.itemTargets.forEach(function (item) {
            if (searchQuery.length === 0) {
                item.classList.remove(self.irrelevantResultClass)
                return
            }

            const searchTerms = JSON.parse(item.dataset.searchTerms)
            const hasMatchingTerms = searchTerms.some(function (term) {
                return localeIncludes(term, searchQuery)
            })
            if (hasMatchingTerms) {
                item.classList.remove(self.irrelevantResultClass)
            } else {
                item.classList.add(self.irrelevantResultClass)
            }
        })
    }

    /* Static fields */
    SearchController.targets = ["searchBar", "item"]
    SearchController.classes = ["irrelevantResult"]

    function init() {
        // Make search bar visible
        const els = document.getElementsByClassName("user-search")
        for (var i = 0; i < els.length; i++) {
            els.item(i).removeAttribute("hidden");
        }

        const application = Stimulus.Application.start();
        application.register("search", SearchController);
    }

    window.addEventListener("load", init);
})();
