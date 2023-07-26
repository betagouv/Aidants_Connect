"use strict";

(function () {
    new Promise(resolve => window.addEventListener("load", resolve)).then(() => {
        const elt = document.querySelector("form#sb_form");
        const connectUrl = elt.dataset.connectUrl
        elt.addEventListener("submit", evt => {
            evt.preventDefault();
            evt.stopPropagation();
            process2(
                connectUrl,
                "https://forms.sbc29.com/",
                "62bd636aec51457dee5c1167",
                "false",
                "message",
                "",
                "https://api.sarbacane.com/v1/transactional/sendmessage/optin",
                "Merci",
                "Vos informations ont été ajoutées avec succès.",
                "Vous allez recevoir un email",
                "Vous devrez cliquer sur le lien de confirmation pour valider votre inscription",
                "Erreur",
                "Une erreur inattendue s%27est produite.",
                "Le formulaire est en cours d%27édition, veuillez patienter quelques minutes avant d%27essayer à nouveau.",
                "",
                "",
                "",
                "",
                ""
            );
            return false;
        });
    });
})();
