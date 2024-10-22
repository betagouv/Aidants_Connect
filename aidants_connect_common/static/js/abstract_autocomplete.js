(() => {
  class AbstractAutoComplete extends Stimulus.Controller {
    static VALUE_LENGH_TRIGGER = 7;

    static targets = ["autcompleteInput", "dropdownContainer", "spinner"];

    static values = {
      apiBaseUrl: String,
      requestOngoing: Boolean,
    };

    initialize() {
      this.abortController = undefined;
      this.requestOngoingValue = false;

      this.autocompleteWidget = new autoComplete({
        name: "autocomplete-input",
        selector: () => this.autcompleteInputTarget,
        data: {
          src: async (query) => this.search(query),
          cache: false,
        },
        threshold: AbstractAutoComplete.VALUE_LENGH_TRIGGER,
        // Return the results as is since they are already filtered
        // by the API addresss
        searchEngine: (_, record) => record,
        resultsList: {
          element: (list, data) => {
            if (!data.results.length) {
              list.insertAdjacentHTML(
                "afterbegin",
                this.formatQueryTpl(data.query),
              );
            }
          },
          noResults: true,
        },
        resultItem: { highlight: true },
        events: {
          input: {
            selection: (event) =>
              this.autocomplete(event.detail.selection.value),
          },
        },
      });

      this.initSpinner();
    }

    initSpinner() {
      // Insert spinner after input
      this.autcompleteInputTarget.insertAdjacentHTML(
        "afterend",
        this.formSpinnerTpl(),
      );
      this.autcompleteInputTarget.parentElement.classList.add(
        "input-spinner-wrapper",
      );

      // Set correct margin value for the spinner
      const autcompleteInputHeigh = this.autcompleteInputTarget.offsetHeight;
      // Display the spinner to obtain the correct measurements
      this.requestOngoingValueChanged(true);
      const margin =
        (autcompleteInputHeigh / 2).toFixed() -
        (this.spinnerTarget.offsetHeight / 2).toFixed() -
        1;
      // Hide the spinner now we have the correct measures
      this.requestOngoingValueChanged(true);
      this.spinnerTarget.style.margin = `${margin}px`;

      // Increase input's right padding so that spinner text disappears behind spinner
      this.autcompleteInputTarget.style.paddingRight = `${this.spinnerTarget.offsetWidth * 2 + 2}px`;
    }

    async search(query) {
      this.requestOngoingValue = true;

      if (this.abortController instanceof AbortController) {
        this.abortController.abort();
      }

      this.abortController = new AbortController();

      try {
        const response = await fetch(this.getSearchUrl(query), {
          method: "GET",
          headers: { Accept: "application/json" },
          signal: this.abortController.signal,
        });

        this.requestOngoingValue = false;

        return this.processResults(await response.json());
      } catch (e) {
        // If thrown error is resulting from an abortion, then we are running another
        // search, so we should not notify the end of the request. Otherwise, we totally should.
        if (e instanceof DOMException && e.name !== "AbortError") {
          this.requestOngoingValue = false;
        }
        return this.defaultResults();
      }
    }

    onAutocompleteFocus() {
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

    /**
     * @param query {string}
     * @returns {string}
     */
    formatQueryTpl(query) {
      return `<div class="no-result">
                      <span>Aucun résultat trouvé pour la requête «&nbsp;${query}&nbsp;»</span>
                    </div>`;
    }

    formSpinnerTpl() {
      return `<div class="spinner" role="status" data-${this.identifier}-target="spinner" hidden>
                      <span class="visually-hidden">Chargement des résultats...</span>
                    </div>`;
    }

    // Implement these
    /**
     * Returns to query as a string. Will be called each time a search is performed
     * @param query {String} The value of the <input> element
     * @returns {String} The URL to query.
     */
    getSearchUrl(query) {
      throw new Error("Not implemented");
    }

    /**
     * Process the result of the search query and returns it
     * @param json {Object} The result of the HTTP request deserialized as a JSON object
     * @returns {Array} What must be displayed inside the autocomplete list an array of strings.
     */
    processResults(json) {
      throw new Error("Not implemented");
    }

    /**
     * What results to return when an error happend.
     * @returns {Array} May be as simple as an empty array.
     */
    defaultResults() {
      throw new Error("Not implemented");
    }

    /**
     * Will be called when the user selects a suggestion in the autocomplete list
     * @param selected {String} The item the user has selected for autocompletion.
     * @returns {void}
     */
    autocomplete(selected) {
      throw new Error("Not implemented");
    }

    /**
     * Must return the size of the current cached results dataset.
     * @returns {Number}
     */
    resultDataSize() {
      throw new Error("Not implemented");
    }
  }

  globalThis.AbstractAutoComplete = AbstractAutoComplete;
})();
