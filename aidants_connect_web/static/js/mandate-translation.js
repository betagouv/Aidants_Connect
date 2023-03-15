"use strict";

(function () {
    const MandateTranslation = Object.extendClass(Stimulus.Controller);

    Object.assign(MandateTranslation.prototype, {
        "connect": function connect() {
            this.langCodeValue = document.querySelector(
                "#mandate-translation-lang"
            ).value;
        },

        "langCodeValueChanged": function langCodeValueChanged() {
            if (this.langCodeValue === "") {
                return this.setContainerContent(undefined);
            }

            var xhr = new XMLHttpRequest();
            xhr.responseType = "text";
            xhr.timeout = 15000;
            xhr.addEventListener("load", this.onResponse.bind(this));

            const form = new FormData();
            form.append("lang_code", this.langCodeValue);
            xhr.open("POST", this.translationEndpointValue, true);
            xhr.setRequestHeader("Accept", "text/html");
            xhr.send(form);
        },

        "onResponse": function onResponse(evt) {
            if (evt.target.status === 200) {
                this.setContainerContent(evt.target.response);
            } else {
                this.setContainerContent(undefined);
            }
        },

        "print": function print() {
            window.print();
        },

        "setContainerContent": function setContainerContent(html) {
            if (html === undefined) {
                this.translationContainerTarget.innerHTML = this.emptyTranslationTplTarget.innerHTML;
                this.translationContainerTarget.removeAttribute("lang");
                this.translationContainerTarget.classList.add(this.noprintClass);
            } else {
                this.translationContainerTarget.innerHTML = html;
                this.translationContainerTarget.setAttribute("lang", this.langCodeValue);
                this.translationContainerTarget.classList.remove(this.noprintClass);
            }
        },

        "selectTranslation": function selectTranslation(evt) {
            this.langCodeValue = evt.target.value.trim();
        },
    });

    MandateTranslation.classes = [
        "noprint",
    ];

    MandateTranslation.targets = [
        "translationContainer",
        "emptyTranslationTpl",
    ];

    MandateTranslation.values = {
        "translationEndpoint": String,
        "langCode": String,
    };



    function init() {
        const application = Stimulus.Application.start();
        application.register("mandate-translation", MandateTranslation);
    }

    window.addEventListener("load", init);
})();
