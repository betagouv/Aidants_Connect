import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class FormationTypeController extends BaseController {
  static targets = ["emailFormateurSection", "emailFormateurField"];
  static values = { p2pValue: String };

  connect() {
    console.log("FormationTypeController connected");
    console.log("P2P value:", this.p2pValueValue);
    this.toggleEmailFormateur();
  }

  typeChanged(event) {
    console.log("Type changed event triggered");
    this.toggleEmailFormateur();
  }

  toggleEmailFormateur() {
    const selectedValue = document.querySelector(
      'input[name="multiform-course_type-type"]:checked'
    )?.value;
    console.log("Selected value:", selectedValue);
    console.log("P2P value:", this.p2pValueValue);
    const isP2P = selectedValue === this.p2pValueValue;
    console.log("Is P2P:", isP2P);

    // Show/hide both the description and the field using hidden attribute
    if (isP2P) {
      console.log("Showing email formateur fields");
      this.emailFormateurSectionTarget.removeAttribute("hidden");
      this.emailFormateurFieldTarget.removeAttribute("hidden");
    } else {
      console.log("Hiding email formateur fields");
      this.emailFormateurSectionTarget.setAttribute("hidden", "");
      this.emailFormateurFieldTarget.setAttribute("hidden", "");
    }

    // Make field required/optional based on selection
    const emailInput = this.emailFormateurFieldTarget.querySelector(
      'input[type="email"]'
    );
    if (emailInput) {
      this.mutateRequirement(isP2P, emailInput);
      if (!isP2P) {
        emailInput.value = "";
      }
    }
  }
}

aidantsConnectApplicationReady.then((application) => {
  application.register("formation-type", FormationTypeController);
});
