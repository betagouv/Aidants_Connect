(function () {
    new Promise(resolve => window.addEventListener("load", resolve)).then(() => {
        const videoUrl = document.querySelector("#lightbox-video-script").dataset.videoUrl;
        document.querySelector('button.lightbox-video').addEventListener("click", () => {
            basicLightbox.create(
                `<video controls data-id="2"><source src="${videoUrl}" type="video/mp4"></video>`
            ).show()
        });
    });
})();
