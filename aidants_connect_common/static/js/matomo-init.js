(() => {
  const el = document.querySelector("#matomo-script");
  const matomoUrl = el.dataset.matomoUrl.replace(/\/+$/, "");
  const matomoSiteId = el.dataset.matomoSiteId;
  // biome-ignore  lint/suspicious/noAssignInExpressions: tartaucitron's code; don't touch
  const _paq = (window._paq = window._paq || []);
  _paq.push(["trackPageView"]);
  _paq.push(["enableLinkTracking"]);
  (() => {
    _paq.push(["setTrackerUrl", `${matomoUrl}/matomo.php`]);
    _paq.push(["setSiteId", matomoSiteId]);
    const script = document.createElement("script");
    script.async = true;
    script.src = `${matomoUrl}/matomo.js`;
    document.querySelector("body").insertAdjacentElement("beforeend", script);
  })();
})();
