(function () {
    window.addEventListener("load", function () {
        // init
        let mandat_is_remote_checkbox = document.getElementById("id_is_remote");
        let mandat_duree_label_is_remote_span = document.getElementsByClassName("duree-label-is-remote");
        for (let i = 0; i < mandat_duree_label_is_remote_span.length; i++) {
            mandat_duree_label_is_remote_span[i].style.display = "none";
        }

        function toggle_phone_number_panel(checked) {
            // TODO: Reactivate when SMS consent is a thing
            return;
            let phone_number_panel = document.getElementById("phone_number_panel");

            if(checked) {
                phone_number_panel.removeAttribute("hidden");
                phone_number_panel.setAttribute("aria-hidden", "false");
            } else {
                phone_number_panel.setAttribute("hidden", "");
                phone_number_panel.setAttribute("aria-hidden", "true");
            }
        }

        toggle_phone_number_panel(mandat_is_remote_checkbox.checked)

        // toggle mandat_is_remote
        mandat_is_remote_checkbox.addEventListener('change', function (evt) {
            for (let i = 0; i < mandat_duree_label_is_remote_span.length; i++) {
                mandat_duree_label_is_remote_span[i].style.display = this.checked ? "initial" : "none";
            }

            toggle_phone_number_panel(evt.target.checked);
        });
    })
})();
