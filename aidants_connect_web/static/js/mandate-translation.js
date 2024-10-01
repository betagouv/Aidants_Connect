(() => {
  class MandateTranslation extends Stimulus.Controller {
    connect() {
      this.langCodeValue = document.querySelector(
        "#mandate-translation-lang",
      ).value;
    }

    selectTranslation(evt) {
      this.langCodeValue = evt.target.value.trim();
    }

    langCodeValueChanged() {
      if (this.langCodeValue === "") {
        return this.setContainerContent(undefined);
      }

      const form = new FormData();
      form.append("lang_code", this.langCodeValue);

      fetch(this.translationEndpointValue, {
        body: form,
        method: "post",
      }).then((response) => {
        if (response.ok)
          response.text().then(this.setContainerContent.bind(this));
        else this.setContainerContent(undefined);
      });
    }

    print() {
      window.print();
    }

    setContainerContent(html) {
      if (html === undefined) {
        this.translationContainerTarget.innerHTML =
          this.emptyTranslationTplTarget.innerHTML;
        this.translationContainerTarget.removeAttribute("lang");
        this.translationContainerTarget.classList.add(this.noprintClass);
      } else {
        this.translationContainerTarget.innerHTML = html;
        this.translationContainerTarget.setAttribute(
          "lang",
          this.langCodeValue,
        );
        this.translationContainerTarget.classList.remove(this.noprintClass);
      }
    }

    static classes = ["noprint"];
    static targets = ["translationContainer", "emptyTranslationTpl"];
    static values = {
      translationEndpoint: String,
      langCode: String,
    };
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("mandate-translation", MandateTranslation);
    },
  );
})();
