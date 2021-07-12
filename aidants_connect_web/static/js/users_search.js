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

    const FilterController = extend(Stimulus.Controller);

    /*
     * This was made with Stimulus framework
     * https://stimulus.hotwired.dev
     */
    FilterController.prototype.onInputValueChanged = function (evt) {
        this.searchValue = evt.target.value.trim();
    }

    /** Returns true if the second string contians the first, case-agnostic */
    FilterController.prototype.stringContains = function (first, second) {
        return first.toLocaleLowerCase().indexOf(second.toLocaleLowerCase()) !== -1;
    }

    FilterController.prototype.searchValueChanged = function () {
        if (this.searchValue.length === 0) {
            this.element.classList.remove(this.irrelevantResultClass);
            return;
        }

        var matchedResult = (
            this.stringContains(this.familynameValue, this.searchValue) ||
            this.stringContains(this.firstnameValue, this.searchValue)
        );

        if (!matchedResult) {
            this.element.classList.add(this.irrelevantResultClass);
        } else {
            this.element.classList.remove(this.irrelevantResultClass);
        }
    }

    FilterController.prototype.connect = function () {
        const self = this
        document
            .getElementById("filter-input")
            .addEventListener("input", function (evt) {
                self.onInputValueChanged(evt);
            });
    }

    /* Static fields */
    FilterController.classes = ["irrelevantResult"]
    FilterController.values = {
        firstname: String,
        familyname: String,
        search: String
    }

    function init() {
        // Make search bar visible
        const els = document.getElementsByClassName("user-search")
        for (var i = 0; i < els.length; i++) {
            els.item(i).removeAttribute("hidden");
        }

        const application = Stimulus.Application.start();
        application.register("filter", FilterController);
    }

    window.addEventListener("load", init);
})();
