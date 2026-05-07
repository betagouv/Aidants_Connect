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
        "useExternalCss": true,
        "useExternalJs": false,
        "readmoreLink": "",
        "mandatory": true,
        "mandatoryCta": true,
    });

    const focusCookieBanner = () => {
        const bannerContainer = document.querySelector("#tarteaucitronAlertBig");
        if (!bannerContainer || bannerContainer.offsetParent === null) {
            return false;
        }

        const firstFocusable = bannerContainer.querySelector(
            'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
        );
        if (!firstFocusable) {
            return false;
        }

        firstFocusable.focus();
        return true;
    };

    const stopWatchingWhenFocused = () => {
        if (focusCookieBanner()) {
            observer.disconnect();
            return true;
        }
        return false;
    };

    const observer = new MutationObserver(() => {
        stopWatchingWhenFocused();
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Handle cases where the banner is already in the DOM.
    if (stopWatchingWhenFocused()) {
        return;
    }

    // Safety net to avoid keeping a long-running observer.
    window.setTimeout(() => observer.disconnect(), 5000);
})();
