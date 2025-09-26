import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class OrganisationChoice extends BaseController {
  static targets = ["siretInput", "submitButton", "alertBox"];

  connect() {
    // Écouter les changements du champ SIRET
    if (this.hasSiretInputTarget) {
      this.siretInputTarget.addEventListener(
        "input",
        this.onSiretChange.bind(this)
      );
    }

    // Écouter les changements des boutons radio pour les choix d'organisation
    this.setupRadioListeners();
  }

  setupRadioListeners() {
    const radioButtons = this.element.querySelectorAll(
      'input[name="organisation_choice"]'
    );
    radioButtons.forEach((radio) => {
      radio.addEventListener(
        "change",
        this.onOrganisationChoiceChange.bind(this)
      );
    });
  }

  onOrganisationChoiceChange(event) {
    if (this.hasSubmitButtonTarget) {
      const selectedRadio = event.target;

      // Cacher toutes les alertes d'abord
      this.alertBoxTargets.forEach((alert) => {
        alert.hidden = true;
      });

      // Activer le bouton si "Ma structure n'apparaît pas dans la liste" est sélectionnée (value="0")
      if (selectedRadio.value === "0") {
        this.submitButtonTarget.disabled = false;
      } else {
        this.submitButtonTarget.disabled = true;

        // Afficher l'alerte correspondant à l'organisation sélectionnée
        const alertInSameElement = selectedRadio
          .closest(".fr-fieldset__element")
          .querySelector('[data-organisation-choice-target="alertBox"]');
        if (alertInSameElement) {
          alertInSameElement.hidden = false;
        }
      }
    }
  }

  onSiretChange() {
    const siretValue = this.siretInputTarget.value.trim();

    if (siretValue === "") {
      // Recharger la page pour revenir à l'état initial
      window.location.href = window.location.pathname;
    }
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("organisation-choice", OrganisationChoice)
);
