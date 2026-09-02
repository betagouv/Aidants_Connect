/**
 * Apply custom bar colors on DSFR <bar-line-chart> components.
 * DSFR Chart only exposes named palettes, so we tint bars after mount.
 */
function applyBarColor (el) {
  const color = el.getAttribute("data-bar-color")
  if (!color) {
    return true
  }

  const instance = el._instance
  const chart = instance?.proxy?.chart
  const data = instance?.data
  if (!chart || !data) {
    return false
  }

  data.colorBarParse = [color]
  data.colorBarHover = [color]

  for (const dataset of chart.data.datasets) {
    if (dataset.type !== "bar") {
      continue
    }
    dataset.backgroundColor = color
    dataset.hoverBackgroundColor = color
    dataset.borderColor = color
  }

  const barLegendDot = el.querySelector(".legend_dot")
  if (barLegendDot) {
    barLegendDot.style.backgroundColor = color
  }

  chart.update("none")
  return true
}

function applyAllBarColors () {
  const charts = document.querySelectorAll("bar-line-chart[data-bar-color]")
  let pending = 0
  charts.forEach((el) => {
    if (!applyBarColor(el)) {
      pending += 1
    }
  })
  return pending === 0
}

function watchBarColors () {
  if (applyAllBarColors()) {
    return
  }

  let attempts = 0
  const maxAttempts = 40
  const timer = window.setInterval(() => {
    attempts += 1
    if (applyAllBarColors() || attempts >= maxAttempts) {
      window.clearInterval(timer)
    }
  }, 100)
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", watchBarColors)
} else {
  watchBarColors()
}
