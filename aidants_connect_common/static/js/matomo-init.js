(function () {
    const matomoUrl = document.querySelector("#matomo-script").dataset.matomoUrl;
    const matomoSiteId = document.querySelector("#matomo-script").dataset.matomoSiteId;
    var _paq = window._paq = window._paq || [];
    /* tracker methods like "setCustomDimension" should be called before "trackPageView" */
    _paq.push(["trackPageView"]);
    _paq.push(["enableLinkTracking"]);
    (function () {
        _paq.push(["setTrackerUrl", matomoUrl + "matomo.php"]);
        _paq.push(["setSiteId", matomoSiteId]);
        var d = document, g = d.createElement("script"), s = d.getElementsByTagName("script")[0];
        g.async = true;
        g.src = "https://cdn.matomo.cloud/gouv.matomo.cloud/matomo.js";
        s.parentNode.insertBefore(g, s);
    })();
})();
