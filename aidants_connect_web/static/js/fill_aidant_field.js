(() => {
  window.addEventListener("load", () => {
    const id_aidant_field = document.getElementById("id_aidant");
    const id_aidant_value = document.getElementById("id_aidant_value");
    if (id_aidant_value) {
      id_aidant_field.value = Number.parseInt(
        id_aidant_value.innerText.trim(),
        10,
      );
      id_aidant_field.type = "hidden";
      id_aidant_field.closest("fieldset").classList.add("hidden");
    }
  });
})();
