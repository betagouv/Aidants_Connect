(() => {
  // This JS code won't be executed on IE11, so we can write ES6 code
  class Address extends Object {
    constructor({ id, name, score, postcode, city, citycode, context }) {
      super();
      this.id = id;
      this.street = name;
      this.score = score;
      this.zipcode = postcode;
      this.city = city;
      this.cityInseeCode = citycode;
      this.dptInseeCode = context.split(",")[0];
    }

    toString() {
      return `${this.street} ${this.zipcode} ${this.city} ${this.cityInseeCode} ${this.dptInseeCode}`;
    }
  }

  class AddressAutoComplete extends AbstractAutoComplete {
    API_RESPONSE_LIMIT = 5;

    static targets = [
      ...AbstractAutoComplete.targets,
      "zipcodeInput",
      "cityInput",
      "cityInseeCodeInput",
      "dptInseeCodeInput",
    ];

    static values = {
      ...AbstractAutoComplete.values,
      apiBaseUrl: String,
      requestOngoing: Boolean,
    };

    initialize() {
      this.addresses = {};
      this.labels = [];

      // Insert <input> to disable backend validation for address
      this.autcompleteInputTarget.insertAdjacentHTML(
        "afterend",
        '<input name="skip_backend_validation" value="true" hidden>',
      );

      super.initialize();
    }

    getSearchUrl(query) {
      const dest = new URL(this.apiBaseUrlValue);
      dest.searchParams.append("q", query);
      dest.searchParams.append("limit", `${this.API_RESPONSE_LIMIT}`);
      return dest.toString();
    }

    processResults(json) {
      const addresses = {};
      this.labels.length = 0;

      json.features.forEach((item) => {
        const address = item.properties;
        addresses[address.label] = new Address(address);
        this.labels.push(address.label);
      });

      this.addresses = addresses;
      return this.labels;
    }

    defaultResults() {
      return this.labels;
    }

    autocomplete(selected) {
      const result = this.addresses[selected];
      if (selected) {
        this.autcompleteInputTarget.value = result.street;
        this.zipcodeInputTarget.value = result.zipcode;
        this.cityInputTarget.value = result.city;
        this.cityInseeCodeInputTarget.value = result.cityInseeCode;
        this.dptInseeCodeInputTarget.value = result.dptInseeCode;
      }
    }

    resultDataSize() {
      return Object.keys(this.addresses).length;
    }
  }

  if (window.fetch) {
    window.addEventListener("load", () =>
      Stimulus.Application.start().register(
        "address-autocomplete",
        AddressAutoComplete,
      ),
    );
  }
})();
