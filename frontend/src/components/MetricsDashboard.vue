<template>
  <div class="metrics-dashboard">
    <h3 class="dashboard-title">Metrics</h3>
    <div class="charts-grid">
      <div v-for="name in metricNames" :key="name" class="chart-card">
        <div class="chart-header">{{ formatName(name) }}</div>
        <canvas :ref="el => chartRefs[name] = el" class="chart-canvas" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  metrics: { type: Object, default: () => ({}) },
  currentTimestep: { type: Number, default: 0 },
  events: { type: Array, default: () => [] },
})

const chartRefs = ref({})

const metricNames = [
  'idea_entropy', 'polarization_index', 'clustering_coefficient',
  'institutional_cohesion', 'resource_gini', 'cascade_count',
  'feedback_loop_strength', 'total_energy',
]

function formatName(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function drawChart(name) {
  const canvas = chartRefs.value[name]
  if (!canvas) return
  const series = props.metrics[name] || []
  if (!series.length) return

  const ctx = canvas.getContext('2d')
  const w = canvas.parentElement.clientWidth - 2
  const h = 60
  canvas.width = w * devicePixelRatio
  canvas.height = h * devicePixelRatio
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`
  ctx.scale(devicePixelRatio, devicePixelRatio)

  ctx.clearRect(0, 0, w, h)

  const values = series.map(p => p[1])
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min
  const pad = 4
  const isFlat = range < 0.001

  if (isFlat) {
    // Draw flat indicator — dashed horizontal line with value label
    ctx.beginPath()
    ctx.strokeStyle = '#30363d'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.moveTo(pad, h / 2)
    ctx.lineTo(w - pad, h / 2)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#484f58'
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(`constant: ${values[0].toFixed(2)}`, w / 2, h / 2 - 6)
  } else {
    // Line chart with gradient fill
    ctx.beginPath()
    ctx.strokeStyle = '#58a6ff'
    ctx.lineWidth = 1.5
    const points = []
    for (let i = 0; i < series.length; i++) {
      const x = pad + (i / Math.max(1, series.length - 1)) * (w - 2 * pad)
      const y = h - pad - ((values[i] - min) / range) * (h - 2 * pad)
      points.push([x, y])
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.stroke()

    // Fill area under curve
    if (points.length > 1) {
      ctx.beginPath()
      ctx.moveTo(points[0][0], h)
      for (const [x, y] of points) ctx.lineTo(x, y)
      ctx.lineTo(points[points.length - 1][0], h)
      ctx.closePath()
      const gradient = ctx.createLinearGradient(0, 0, 0, h)
      gradient.addColorStop(0, 'rgba(88, 166, 255, 0.15)')
      gradient.addColorStop(1, 'rgba(88, 166, 255, 0.02)')
      ctx.fillStyle = gradient
      ctx.fill()
    }

    // Current value dot
    if (props.currentTimestep > 0 && series.length > 1) {
      const idx = series.findIndex(p => p[0] >= props.currentTimestep)
      if (idx >= 0 && points[idx]) {
        // Value at current timestep
        ctx.beginPath()
        ctx.arc(points[idx][0], points[idx][1], 3, 0, 2 * Math.PI)
        ctx.fillStyle = '#f0883e'
        ctx.fill()

        // Vertical marker
        ctx.beginPath()
        ctx.strokeStyle = '#f0883e'
        ctx.lineWidth = 1
        ctx.globalAlpha = 0.3
        ctx.setLineDash([3, 3])
        ctx.moveTo(points[idx][0], 0)
        ctx.lineTo(points[idx][0], h)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.globalAlpha = 1
      }
    }
  }

  // Value label (min/max for dynamic, value for flat)
  ctx.fillStyle = '#8b949e'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'right'
  if (!isFlat) {
    // Show current value at cursor position
    if (props.currentTimestep > 0 && series.length > 1) {
      const idx = series.findIndex(p => p[0] >= props.currentTimestep)
      if (idx >= 0) {
        ctx.fillText(values[idx].toFixed(2), w - 4, 12)
      } else {
        ctx.fillText(values[values.length - 1].toFixed(2), w - 4, 12)
      }
    } else {
      ctx.fillText(values[values.length - 1].toFixed(2), w - 4, 12)
    }
    // Show range
    ctx.fillStyle = '#484f58'
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(`${min.toFixed(1)}–${max.toFixed(1)}`, 4, 12)
  }
}

function drawAll() {
  nextTick(() => {
    for (const name of metricNames) drawChart(name)
  })
}

watch(() => props.metrics, drawAll, { deep: true })
watch(() => props.currentTimestep, drawAll)
onMounted(drawAll)
</script>

<style scoped>
.metrics-dashboard {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #161b22;
  border-radius: 8px;
  overflow-y: auto;
}
.dashboard-title {
  margin: 0 0 4px;
  color: #e6edf3;
  font-size: 14px;
  font-weight: 600;
}
.charts-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.chart-card {
  background: #0d1117;
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 6px 8px;
}
.chart-header {
  font-size: 11px;
  color: #8b949e;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.chart-canvas {
  display: block;
  width: 100%;
}
</style>
