"use strict";

(function () {
    // This JS code won't be executed on IE11, so we can write ES6 code
    class Address extends Object {
        constructor({id, name, score, postcode, city}) {
            super();
            this.id = id;
            this.street = name;
            this.score = score;
            this.zipcode = postcode;
            this.city = city;
        }

        toString() {
            return `${this.street} ${this.zipcode} ${this.city}`
        }
    }

    class AddressAutoComplete extends Stimulus.Controller {
        VALUE_LENGH_TRIGGER = 7;
        API_RESPONSE_LIMIT = 5;

        initialize() {
            this.addresses = {};
            this.abortController = undefined;
            this.autocomplete = new autoComplete({
                name: "address-autocomplete",
                selector: () => this.addressInputTarget,
                data: {
                    src: async query => this.search(query),
                    cache: false
                },
                threshold: this.VALUE_LENGH_TRIGGER,
                resultsList: {
                    element: (list, data) => {
                        if (!data.results.length) {
                            const html = this.noResultTplTarget.innerHTML.replace(/__query__/gm, `"${data.query}"`);
                            list.insertAdjacentHTML("afterbegin", html);
                        }
                    },
                    noResults: true,
                },
                resultItem: {
                    highlight: true
                },
                events: {
                    input: {
                        selection: (event) => {
                            const result = this.addresses[event.detail.selection.value];
                            if (result) {
                                this.addressInputTarget.value = result.street;
                                this.zipcodeInputTarget.value = result.zipcode;
                                this.cityInputTarget.value = result.city;
                            }
                        }
                    }
                }
            });
        }

        async search(query) {
            let dest = new URL(this.apiBaseUrlValue);
            dest.searchParams.append("q", query);
            dest.searchParams.append("limit", `${this.API_RESPONSE_LIMIT}`);

            if (this.abortController instanceof AbortController) {
                this.abortController.abort();
            }

            this.abortController = new AbortController();

            const response = await fetch(dest.toString(), {
                method: "GET",
                headers: {"Accept": "application/json"},
                signal: this.abortController.signal,
            });

            const json = await response.json();
            const addresses = {};
            const values = []

            json.features.forEach(item => {
                const address = item.properties;
                addresses[address.label] = new Address(address);
                values.push(address.label);
            });

            this.addresses = addresses;
            return values;
        }

        static targets = [
            "addressInput",
            "zipcodeInput",
            "cityInput",
            "dropdownContainer",
            "noResultTpl",
        ]
        static values = {"apiBaseUrl": String}
    }

    if (window.fetch) {
        window.addEventListener("load", () =>
            Stimulus.Application.start().register("address-autocomplete", AddressAutoComplete)
        );
    }
})();
