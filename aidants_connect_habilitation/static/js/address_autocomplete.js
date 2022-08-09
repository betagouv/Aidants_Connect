"use strict";

(function () {
    // This JS code won't be executed on IE11, so we can write ES6 code
    class Address extends Object {
        constructor({id, name, score, postcode, city, citycode}) {
            super();
            this.id = id;
            this.street = name;
            this.score = score;
            this.zipcode = postcode;
            this.city = city;
            this.codeinsee = citycode;
        }

        toString() {
            return `${this.street} ${this.zipcode} ${this.city} ${this.codeinsee}`
        }
    }

    class AddressAutoComplete extends Stimulus.Controller {
        VALUE_LENGH_TRIGGER = 7;
        API_RESPONSE_LIMIT = 5;


        initialize() {
            this.addresses = {};
            this.labels = []
            this.abortController = undefined;

            this.requestOngoingValue = false;

            // Insert <input> to disable backend validation for address
            this.addressInputTarget.insertAdjacentHTML(
                "afterend", '<input name="skip_backend_validation" value="true" hidden>'
            );

            this.autocomplete = new autoComplete({
                name: "address-autocomplete",
                selector: () => this.addressInputTarget,
                data: {
                    src: async query => this.search(query),
                    cache: false
                },
                threshold: this.VALUE_LENGH_TRIGGER,
                // Return the results as is since they are already filtered
                // by the API addresss
                searchEngine: (_, record) => record,
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
                                this.codeinseeInputTarget.value = result.codeinsee;
                            }
                        }
                    }
                }
            });

            this.initSpinner();
        }

        initSpinner() {
            // Insert spinner after input
            this.addressInputTarget.insertAdjacentHTML("afterend", this.spinnerTplTarget.innerHTML);
            this.addressInputTarget.parentElement.classList.add("input-spinner-wrapper");

            // Set correct margin value for the spinner
            const addressInputHeigh = this.addressInputTarget.offsetHeight;
            // Display the spinner to obtain the correct measurements
            this.requestOngoingValueChanged(true);
            const margin = (addressInputHeigh / 2).toFixed() - (this.spinnerTarget.offsetHeight / 2).toFixed() - 1;
            // Hide the spinner now we have the correct measures
            this.requestOngoingValueChanged(true);
            this.spinnerTarget.style.margin = `${margin}px`;

            // Increase input's right padding so that spinner text disappears behind spinner
            this.addressInputTarget.style.paddingRight = `${this.spinnerTarget.offsetWidth * 2 + 2}px`;
        }

        async search(query) {
            let dest = new URL(this.apiBaseUrlValue);
            dest.searchParams.append("q", query);
            dest.searchParams.append("limit", `${this.API_RESPONSE_LIMIT}`);

            this.requestOngoingValue = true;

            if (this.abortController instanceof AbortController) {
                this.abortController.abort();
            }

            this.abortController = new AbortController();

            try {
                var response = await fetch(dest.toString(), {
                    method: "GET",
                    headers: {"Accept": "application/json"},
                    signal: this.abortController.signal,
                });

                this.requestOngoingValue = false;

                const json = await response.json();
                const addresses = {};
                this.labels.length = 0;

                json.features.forEach(item => {
                    const address = item.properties;
                    addresses[address.label] = new Address(address);
                    this.labels.push(address.label);
                });

                this.addresses = addresses;
                return this.labels;
            } catch (e) {
                // If thrown error is resulting from an abortion, then we are running another
                // search, so we should not notify the end of the request. Otherwise, we totally should.
                if (e instanceof DOMException && e.name !== "AbortError") {
                    this.requestOngoingValue = false;
                }
                return this.labels;
            }
        }

        onAddressFocus() {
            if (Object.keys(this.addresses).length === 0) {
                // Trigger a first search on focus if input already contains text but cached results are empty
                if (this.addressInputTarget.value.length !== 0) {
                    this.autocomplete.start(this.addressInputTarget.value);
                }
                return;
            }

            // Open the autocomplete list on focus
            this.autocomplete.open();
        }

        requestOngoingValueChanged(ongoing) {
            // During initialization, value may be changed and callback
            // may be trigger without element existing yet.
            if (!this.hasSpinnerTarget) {
                return;
            }

            if (ongoing) {
                this.spinnerTarget.removeAttribute("hidden");
            } else {
                this.spinnerTarget.setAttribute("hidden", "hidden");
            }
        }

        static targets = [
            "addressInput",
            "zipcodeInput",
            "cityInput",
            "codeinseeInput",
            "dropdownContainer",
            "noResultTpl",
            "spinnerTpl",
            "spinner",
        ]
        static values = {
            "apiBaseUrl": String,
            "requestOngoing": Boolean,
        }
    }

    if (window.fetch) {
        window.addEventListener("load", () =>
            Stimulus.Application.start().register("address-autocomplete", AddressAutoComplete)
        );
    }
})();
