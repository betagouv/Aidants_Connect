(function () {
    window.addEventListener("load", function () {
        let id_aidant_field = document.getElementById("id_aidant");
        let id_aidant_value = document.getElementById("id_aidant_value");
        if (id_aidant_value) {
            id_aidant_field.value = parseInt(id_aidant_value.innerText.trim(), 10);
            id_aidant_field.type = "hidden";
            id_aidant_field.closest("fieldset").classList.add("hidden");
        }
    })
})();
