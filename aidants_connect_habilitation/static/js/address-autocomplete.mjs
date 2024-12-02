import {aidantsConnectApplicationReady, BaseController} from "AidantsConnectApplication"
import "autoComplete"

class Address extends Object {
    constructor ({id, name, score, postcode, city, citycode, context}) {
        super();
        this.id = id;
        this.street = name;
        this.score = score;
        this.zipcode = postcode;
        this.city = city;
        this.cityInseeCode = citycode;
        this.dptInseeCode = context.split(",")[0];
    }

    toString () {
        return `${this.street} ${this.zipcode} ${this.city} ${this.cityInseeCode} ${this.dptInseeCode}`
    }
}

class AddressAutoComplete extends BaseController {
    static API_RESPONSE_LIMIT = 5;
    static VALUE_LENGH_TRIGGER = 7;

    static targets = [
        "autcompleteInput",
        "dropdownContainer",
        "spinner",
        "zipcodeInput",
        "cityInput",
        "cityInseeCodeInput",
        "dptInseeCodeInput",
    ]

    static values = {
        "apiBaseUrl": String,
        "requestOngoing": Boolean,
    }

    initialize () {
        this.abortController = undefined;
        this.requestOngoingValue = false;

        this.autocompleteWidget = new window.autoComplete({
            name: "autocomplete-input",
            selector: () => this.autcompleteInputTarget,
            data: {
                src: async query => this.search(query),
                cache: false
            },
            threshold: AddressAutoComplete.VALUE_LENGH_TRIGGER,
            // Return the results as is since they are already filtered
            // by the API addresss
            searchEngine: (_, record) => record,
            resultsList: {
                element: (list, data) => {
                    if (!data.results.length) {
                        list.insertAdjacentHTML("afterbegin", this.formatQueryTpl(data.query));
                    }
                },
                noResults: true,
            },
            resultItem: {highlight: true},
            events: {
                input: {
                    selection: event => this.autocomplete(event.detail.selection.value)
                }
            }
        });

        this.initSpinner();

        this.addresses = {};
        this.labels = [];

        // Insert <input> to disable backend validation for address
        this.autcompleteInputTarget.insertAdjacentHTML(
            "afterend", '<input name="skip_backend_validation" value="true" hidden>'
        );

        super.initialize();
    }


    initSpinner () {
        // Insert spinner after input
        this.autcompleteInputTarget.insertAdjacentHTML("afterend", this.formSpinnerTpl());
        this.autcompleteInputTarget.parentElement.classList.add("input-spinner-wrapper");

        // Set correct margin value for the spinner
        const autcompleteInputHeigh = this.autcompleteInputTarget.offsetHeight;
        // Display the spinner to obtain the correct measurements
        this.requestOngoingValueChanged(true);
        const margin = (autcompleteInputHeigh / 2).toFixed() - (this.spinnerTarget.offsetHeight / 2).toFixed() - 1;
        // Hide the spinner now we have the correct measures
        this.requestOngoingValueChanged(true);
        this.spinnerTarget.style.margin = `${margin}px`;

        // Increase input's right padding so that spinner text disappears behind spinner
        this.autcompleteInputTarget.style.paddingRight = `${this.spinnerTarget.offsetWidth * 2 + 2}px`;
    }

    async search (query) {
        this.requestOngoingValue = true;

        if (this.abortController instanceof AbortController) {
            this.abortController.abort();
        }

        this.abortController = new AbortController();

        try {
            var response = await fetch(this.getSearchUrl(query), {
                method: "GET",
                headers: {"Accept": "application/json"},
                signal: this.abortController.signal,
            });

            this.requestOngoingValue = false;

            return this.processResults(await response.json());
        } catch (e) {
            // If thrown error is resulting from an abortion, then we are running another
            // search, so we should not notify the end of the request. Otherwise, we totally should.
            if (e instanceof DOMException && e.name !== "AbortError") {
                this.requestOngoingValue = false;
            } else {
                console.error(e)
            }
            return this.defaultResults();
        }
    }

    onAutocompleteFocus () {
        if (this.resultDataSize() === 0) {
            // Trigger a first search on focus if input already contains text but cached results are empty
            if (this.autcompleteInputTarget.value.length !== 0) {
                this.autocompleteWidget.start(this.autcompleteInputTarget.value);
            }
            return;
        }

        // Open the autocomplete list on focus
        this.autocompleteWidget.open();
    }

    requestOngoingValueChanged (ongoing) {
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

    /**
     * @param query {string}
     * @returns {string}
     */
    formatQueryTpl (query) {
        return `<div class="no-result">
                      <span>Aucun résultat trouvé pour la requête «&nbsp;${query}&nbsp;»</span>
                    </div>`;
    }

    formSpinnerTpl () {
        return `<div class="spinner" role="status" data-${this.identifier}-target="spinner" hidden>
                      <span class="visually-hidden">Chargement des résultats...</span>
                    </div>`;
    }

    getSearchUrl (query) {
        let dest = new URL(this.apiBaseUrlValue);
        dest.searchParams.append("q", query);
        dest.searchParams.append("limit", `${AddressAutoComplete.API_RESPONSE_LIMIT}`);
        return dest.toString();
    }

    processResults (json) {
        const addresses = {};
        this.labels.length = 0;

        json.features.forEach(item => {
            const address = item.properties;
            addresses[address.label] = new Address(address);
            this.labels.push(address.label);
        });

        this.addresses = addresses;
        return this.labels;
    }

    defaultResults () {
        return this.labels;
    }

    autocomplete (selected) {
        const result = this.addresses[selected];
        if (selected) {
            this.autcompleteInputTarget.value = result.street;
            this.zipcodeInputTarget.value = result.zipcode;
            this.cityInputTarget.value = result.city;
            this.cityInseeCodeInputTarget.value = result.cityInseeCode;
            this.dptInseeCodeInputTarget.value = result.dptInseeCode;
        }
    }

    resultDataSize () {
        return Object.keys(this.addresses).length;
    }
}

aidantsConnectApplicationReady.then(app => app.register("address-autocomplete", AddressAutoComplete))
