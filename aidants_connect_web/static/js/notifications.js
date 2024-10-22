import { BaseController } from "./base-controller.js";

(() => {
  class NotificationController extends BaseController {
    async markRead() {
      const response = await fetch(this.urlValue, {
        method: "DELETE",
        redirect: "manual",
      });
      if (response.ok) {
        this.element.remove();
      }
    }

    static values = { url: String };
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("notification", NotificationController);
    },
  );
})();
