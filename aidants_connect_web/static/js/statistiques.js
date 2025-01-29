import "ChartJS"
import "ChartJSDatalabel"
import {aidantsConnectApplicationReady} from "AidantsConnectApplication"

function chartInit () {
    /** @type {Object.<string, any[]>} */
    const data = JSON.parse(document.querySelector("#data").textContent);
    const ctx = document.querySelector("#mandats-chart").getContext("2d");
    const style = getComputedStyle(document.body);
    const color = style.getPropertyValue("--artwork-minor-blue-france")
    const globalPadding = 16

    window.Chart.defaults.font.family = style.fontFamily
    window.Chart.defaults.backgroundColor = color
    window.Chart.defaults.font.size = style.fontSize

    const icons = data.icons.map(it => {
        const image = new Image();
        image.src = it;
        image.alt = ""
        return image
    })

    function drawIcons (chart, {width}) {
        const {ctx, scales: {x, y}} = chart;
        if (x === undefined || y === undefined) {
            return
        }
        const padding = width > 991 ? globalPadding : 0
        let maxWidth = 0

        icons.forEach((img, idx) => {
            const col = chart.getDatasetMeta(0).data[idx]
            const imgX = (col.x - col.width / 2) + padding
            const imgy = y.bottom + padding
            const imgSize = col.width - 2 * padding
            ctx.drawImage(img, imgX, imgy, imgSize, imgSize)
            maxWidth = Math.max(col.width, maxWidth)
        })
        x.options.ticks.padding = maxWidth - padding
        chart.update()
    }

    const afterDraw = {
        id: "afterDraw",
        afterDraw (chart) {
            drawIcons(chart, {height: window.innerHeight, width: window.innerWidth})
        },
    };

    new window.Chart(ctx, {
        type: "bar",
        data: {
            labels: data.titles,
            datasets: [{
                label: "Nombre de démarches",
                data: data.values,
            }]
        },
        plugins: [window.ChartDataLabels, afterDraw],
        options: {
            responsive: true,
            aspectRatio: 3,
            maintainAspectRatio: false,
            onResize: drawIcons,
            layout: {
                padding: {
                    top: 20,
                    right: 0,
                    bottom: 0,
                    left: 0,
                }
            },
            plugins: {
                legend: {display: false},
                title: {display: false},
                tooltip: {enabled: false},
                datalabels: {
                    color: color,
                    font: {weight: "bold"},
                    anchor: "end",
                    align: "top",
                    clamp: true,
                },
            },
            scales: {
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxRotation: 90,
                        minRotation: 0,
                        autoSkip: false
                    }
                },
                y: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {display: false}
                }
            }
        }
    });
}

aidantsConnectApplicationReady.then(chartInit)
