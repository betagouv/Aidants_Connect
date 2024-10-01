django.jQuery(document).ready(() => {
  django.jQuery("select[data-searchable-radio-select]").select2({
    theme: "admin-autocomplete",
  });
  // Force focus https://github.com/select2/select2/issues/5993
  django.jQuery(document).on("select2:open", (e) => {
    document
      .querySelector(`[aria-controls="select2-${e.target.id}-results"]`)
      .focus();
  });
});
