(() => {
  class AdminFilterSelect extends Stimulus.Controller {
    onChange(evt) {
      window.location.href = evt.target.value;
    }
  }

  new Promise((resolve) => window.addEventListener("load", resolve)).then(
    () => {
      const application = Stimulus.Application.start();
      application.register("admin-filter-select", AdminFilterSelect);
    },
  );
})();
