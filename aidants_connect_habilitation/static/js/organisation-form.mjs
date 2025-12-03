import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class DynamicForm extends BaseController {
  static targets = [
    "typeOtherInputContainer",
    "typeInput",
    "onlyShownIfFranceServices",
    "franceServicesInput",
    "missionDescriptionLabel",
    "avgNbDemarchesLabel",
    "missionDescriptionField",
    "avgNbDemarchesField",
  ];

  static values = {
    typeOther: String,
    associationsValue: String,
  };

  connect() {
    this.mutateVisibility(
      this.typeInputTarget.value === this.typeOtherValue,
      this.typeOtherInputContainerTarget
    );
    this.mutateVisibility(
      this.franceServicesInputTarget.checked,
      this.onlyShownIfFranceServicesTarget
    );

    // Initialize labels and field requirements based on current type
    this.updateFieldsForAssociations(this.typeInputTarget.value);
  }

  onFranceServicesChange(evt) {
    this.mutateVisibility(
      evt.target.checked,
      this.onlyShownIfFranceServicesTarget
    );
  }

  onTypeChange(evt) {
    this.mutateVisibility(
      evt.target.value === this.typeOtherValue,
      this.typeOtherInputContainerTarget
    );

    // Update fields for associations
    this.updateFieldsForAssociations(evt.target.value);

    // Reset errors only when switching TO associations
    const isNowAssociation = evt.target.value === this.associationsValueValue;
    if (isNowAssociation) {
      this.resetFieldErrors();
    }
  }

  updateFieldsForAssociations(selectedType) {
    const isAssociation = selectedType === this.associationsValueValue;

    // Update labels using CSS selectors as fallback
    this.updateFieldLabel("mission_description", isAssociation);
    this.updateFieldLabel("avg_nb_demarches", isAssociation);

    // Update field requirements (for client-side validation)
    if (this.hasMissionDescriptionFieldTarget) {
      this.missionDescriptionFieldTarget.required = !isAssociation;
    }

    if (this.hasAvgNbDemarchesFieldTarget) {
      this.avgNbDemarchesFieldTarget.required = !isAssociation;
    }
  }

  updateFieldLabel(fieldName, isOptional) {
    // Try multiple selectors to find the label
    const selectors = [
      `label[for="id_${fieldName}"]`,
      `[data-dynamic-form-target="${fieldName}Label"]`,
      `.field-${fieldName} label`,
      `#id_${fieldName}_label`,
    ];

    let labelElement = null;
    for (const selector of selectors) {
      labelElement = document.querySelector(selector);
      if (labelElement) break;
    }

    if (labelElement) {
      const originalText = labelElement.textContent.replace(
        " (facultatif)",
        ""
      );
      labelElement.textContent = isOptional
        ? `${originalText} (facultatif)`
        : originalText;
    }
  }

  resetFieldErrors() {
    // Remove error messages for mission_description and avg_nb_demarches
    const fieldsToReset = ["mission_description", "avg_nb_demarches"];

    fieldsToReset.forEach((fieldName) => {
      // Find the field element
      const fieldElement = document.querySelector(`[name="${fieldName}"]`);
      if (!fieldElement) return;

      // Find the DSFR input group container
      const inputGroup = fieldElement.closest(".fr-input-group");
      if (inputGroup) {
        // Remove DSFR error class
        inputGroup.classList.remove("fr-input-group--error");

        // Remove DSFR error messages
        const dsfrErrorMessages = inputGroup.querySelectorAll(
          ".fr-error-text, .fr-message--error, .fr-messages-group .fr-message"
        );
        dsfrErrorMessages.forEach((el) => el.remove());
      }

      // Also handle Django's default error classes as fallback
      const errorElements = document.querySelectorAll(
        `[data-field="${fieldName}"] .errorlist, .field-${fieldName} .errorlist`
      );
      errorElements.forEach((el) => el.remove());

      // Remove error classes from the field itself
      fieldElement.classList.remove("is-invalid", "error");
      fieldElement.removeAttribute("aria-invalid");
      fieldElement.removeAttribute("aria-describedby");
    });
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("dynamic-form", DynamicForm)
);
