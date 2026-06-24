import "ChartJS"
import "ChartJSDatalabel"
import { aidantsConnectApplicationReady } from "AidantsConnectApplication"

function getChartColor () {
    const style = getComputedStyle(document.body)
    return style.getPropertyValue("--artwork-minor-blue-france")
}

function initSimpleBarChart ({ dataId, canvasId, datasetLabel, horizontal = false }) {
    const dataNode = document.querySelector(dataId)
    const canvas = document.querySelector(canvasId)
    if (!dataNode || !canvas) {
        return
    }

    const data = JSON.parse(dataNode.textContent)
    const ctx = canvas.getContext("2d")
    const style = getComputedStyle(document.body)
    const color = getChartColor()

    window.Chart.defaults.font.family = style.fontFamily
    window.Chart.defaults.backgroundColor = color
    window.Chart.defaults.font.size = style.fontSize

    new window.Chart(ctx, {
        type: "bar",
        data: {
            labels: data.titles,
            datasets: [{
                label: datasetLabel,
                data: data.values,
            }]
        },
        plugins: [window.ChartDataLabels],
        options: {
            indexAxis: horizontal ? "y" : "x",
            responsive: true,
            aspectRatio: horizontal ? 1.2 : 3,
            maintainAspectRatio: false,
            layout: {
                padding: horizontal
                    ? { top: 0, right: 48, bottom: 0, left: 0 }
                    : { top: 20, right: 0, bottom: 0, left: 0 },
            },
            plugins: {
                legend: { display: false },
                title: { display: false },
                tooltip: { enabled: false },
                datalabels: {
                    color,
                    font: { weight: "bold" },
                    anchor: "end",
                    align: horizontal ? "right" : "top",
                    clamp: true,
                },
            },
            scales: horizontal
                ? {
                    x: {
                        beginAtZero: true,
                        grid: { display: false, drawBorder: false },
                        ticks: { display: false },
                    },
                    y: {
                        grid: { display: false, drawBorder: false },
                        ticks: { autoSkip: false },
                    },
                }
                : {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: {
                            maxRotation: 90,
                            minRotation: 0,
                            autoSkip: false,
                        },
                    },
                    y: {
                        grid: { display: false, drawBorder: false },
                        ticks: { display: false },
                    },
                },
        }
    })
}

function initDemarchesChart () {
    /** @type {Object.<string, any[]>} */
    const data = JSON.parse(document.querySelector("#data").textContent)
    const ctx = document.querySelector("#mandats-chart").getContext("2d")
    const style = getComputedStyle(document.body)
    const color = getChartColor()
    const globalPadding = 16

    window.Chart.defaults.font.family = style.fontFamily
    window.Chart.defaults.backgroundColor = color
    window.Chart.defaults.font.size = style.fontSize

    const icons = data.icons.map(it => {
        const image = new Image()
        image.src = it
        image.alt = ""
        return image
    })

    function drawIcons (chart, { width }) {
        const { ctx, scales: { x, y } } = chart
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
            drawIcons(chart, { height: window.innerHeight, width: window.innerWidth })
        },
    }

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
                legend: { display: false },
                title: { display: false },
                tooltip: { enabled: false },
                datalabels: {
                    color,
                    font: { weight: "bold" },
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
                    ticks: { display: false }
                }
            }
        }
    })
}

function initEvolutionChart ({ dataId, canvasId, label }) {
    const evolutionNode = document.querySelector(dataId)
    const canvas = document.querySelector(canvasId)
    if (!evolutionNode || !canvas) {
        return
    }

    const data = JSON.parse(evolutionNode.textContent)
    if (data.labels.length === 0) {
        return
    }

    const ctx = canvas.getContext("2d")
    const style = getComputedStyle(document.body)
    const color = getChartColor()

    window.Chart.defaults.font.family = style.fontFamily
    window.Chart.defaults.font.size = style.fontSize

    new window.Chart(ctx, {
        type: "line",
        data: {
            labels: data.labels,
            datasets: [{
                label,
                data: data.values,
                borderColor: color,
                backgroundColor: color,
                fill: false,
                tension: 0.2,
                pointRadius: 3,
            }]
        },
        options: {
            responsive: true,
            aspectRatio: 2.5,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        maxRotation: 90,
                        minRotation: 45,
                        autoSkip: false,
                    },
                },
                y: {
                    beginAtZero: true,
                    grid: { display: false },
                },
            }
        }
    })
}

function chartInit () {
    initDemarchesChart()
    initSimpleBarChart({
        dataId: "#mandats-durees-data",
        canvasId: "#mandats-durees-chart",
        datasetLabel: "Nombre de mandats",
        horizontal: true,
    })
    initEvolutionChart({
        dataId: "#mandats-evolution-data",
        canvasId: "#mandats-evolution-chart",
        label: "Mandats créés",
    })
    initEvolutionChart({
        dataId: "#demarches-evolution-data",
        canvasId: "#demarches-evolution-chart",
        label: "Démarches réalisées",
    })
}

aidantsConnectApplicationReady.then(chartInit)
