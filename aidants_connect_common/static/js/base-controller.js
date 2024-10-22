export class BaseController extends Stimulus.Controller {
  noop() {
    /* Does nothing */
  }
  showElement(elt) {
    elt.removeAttribute("hidden");
    elt.removeAttribute("aria-hidden");
  }

  hideElement(elt) {
    elt.setAttribute("hidden", "hidden");
    elt.setAttribute("aria-hidden", "true");
  }

  mutateVisibility(visibility, elt) {
    if (visibility) this.showElement(elt);
    else this.hideElement(elt);
  }

  mutateRequirement(required, elt) {
    if (required) elt.setAttribute("required", "required");
    else elt.removeAttribute("required");
  }
}
