(function () {
    tarteaucitron.init({
        "privacyUrl": "",
        "bodyPosition": "bottom",
        "hashtag": "#tarteaucitron",
        "cookieName": "tarteaucitron",
        "orientation": "bottom",
        "groupServices": false,
        "showDetailsOnClick": true,
        "serviceDefaultState": "wait",
        "showAlertSmall": false,
        "cookieslist": false,
        "closePopup": false,
        "showIcon": true,
        "iconPosition": "BottomRight",
        "adblocker": false,
        "DenyAllCta": true,
        "AcceptAllCta": true,
        "highPrivacy": true,
        "handleBrowserDNTRequest": false,
        "removeCredit": false,
        "moreInfoLink": true,
        "useExternalCss": false,
        "useExternalJs": false,
        "readmoreLink": "",
        "mandatory": true,
        "mandatoryCta": true,
    });

    const el = document.querySelector("#cookie-banner");
    const matomoUrl = el.dataset.matomoUrl;
    const matomoSiteId = el.dataset.matomoSiteId;
    if (matomoUrl && matomoSiteId) {
        tarteaucitron.user.matomoId = matomoSiteId;
        tarteaucitron.user.matomoHost = matomoUrl.replace(/\/*$/, "/");
        (tarteaucitron.job = tarteaucitron.job || []).push('matomo');
    }
})();
