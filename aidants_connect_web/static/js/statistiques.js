/**
 * DSFR Chart has no custom hex API. Setting dataset colors is not enough:
 * Chart.js keeps resolved element options, so bars stay on the palette until
 * hover (which reads hoverBackgroundColor). Tint both datasets and elements.
 */
function tintBars (chart, color) {
  chart.data.datasets.forEach((dataset, index) => {
    if (dataset.type !== "bar") {
      return
    }
    dataset.backgroundColor = color
    dataset.hoverBackgroundColor = color
    dataset.borderColor = color
    dataset.hoverBorderColor = color

    const meta = chart.getDatasetMeta(index)
    for (const element of meta.data) {
      if (!element?.options) {
        continue
      }
      element.options.backgroundColor = color
      element.options.borderColor = color
    }
  })
}

function applyBarColor (el) {
  const color = el.getAttribute("data-bar-color")
  if (!color) {
    return true
  }

  const proxy = el._instance?.proxy
  const chart = proxy?.chart
  if (!proxy || !chart?.data?.datasets) {
    return false
  }

  if (!proxy._acBarColorPatched) {
    proxy._acBarColorPatched = true

    const originalLoadColors = proxy.loadColors.bind(proxy)
    proxy.loadColors = function () {
      originalLoadColors()
      const next = el.getAttribute("data-bar-color")
      if (next) {
        this.colorBarParse = [next]
        this.colorBarHover = [next]
      }
    }

    const plugins = chart.config.plugins || (chart.config.plugins = [])
    plugins.push({
      id: "acBarColor",
      beforeDatasetsDraw (instance) {
        const next = el.getAttribute("data-bar-color")
        if (next) {
          tintBars(instance, next)
        }
      },
    })
  }

  proxy.colorBarParse = [color]
  proxy.colorBarHover = [color]
  tintBars(chart, color)
  chart.draw()
  return true
}

function applyAll () {
  return [...document.querySelectorAll("bar-line-chart[data-bar-color]")].every(applyBarColor)
}

function start () {
  applyAll()
  document.documentElement.addEventListener("dsfr.theme", () => {
    window.setTimeout(applyAll, 0)
  })
  let n = 0
  const timer = window.setInterval(() => {
    n += 1
    if (applyAll() || n >= 50) {
      window.clearInterval(timer)
    }
  }, 100)
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start)
} else {
  start()
}
