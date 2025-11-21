import {
  BaseController,
  aidantsConnectApplicationReady,
} from "AidantsConnectApplication";

class BaseAidantRequestFormset extends BaseController {
  connect() {
    // Detect browser back navigation and reload page to avoid cached form data
    window.addEventListener("pageshow", (event) => {
      if (event.persisted) {
        // Page was restored from cache (back button), force reload
        window.location.reload();
      }
    });
  }
}

aidantsConnectApplicationReady.then((application) =>
  application.register("base-aidant-request-formset", BaseAidantRequestFormset)
);
