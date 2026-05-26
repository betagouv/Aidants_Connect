import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

/**
 * Toggles visibility of the "new email" field based on the "email_will_change" radio selection.
 * Used on the add-aidant wizard step 2 (structure change formset).
 */
class NewEmailToggleController extends BaseController {
  static targets = ["wrapper"];
  static values = { formPrefix: String };

  connect() {
    this.toggle();
  }

  toggle() {
    const radioName = `${this.formPrefixValue}-email_will_change`;
    const checked = this.element.querySelector(
      `input[name="${radioName}"]:checked`
    );
    const show = checked && checked.value === "True";
    this.mutateVisibility(show, this.wrapperTarget);
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("new-email-toggle", NewEmailToggleController)
);
