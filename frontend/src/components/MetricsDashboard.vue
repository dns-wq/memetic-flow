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
  const range = max - min || 1
  const pad = 4

  // Line
  ctx.beginPath()
  ctx.strokeStyle = '#58a6ff'
  ctx.lineWidth = 1.5
  for (let i = 0; i < series.length; i++) {
    const x = pad + (i / Math.max(1, series.length - 1)) * (w - 2 * pad)
    const y = h - pad - ((values[i] - min) / range) * (h - 2 * pad)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.stroke()

  // Current timestep marker
  if (props.currentTimestep > 0 && series.length > 1) {
    const idx = series.findIndex(p => p[0] >= props.currentTimestep)
    if (idx >= 0) {
      const x = pad + (idx / Math.max(1, series.length - 1)) * (w - 2 * pad)
      ctx.beginPath()
      ctx.strokeStyle = '#f0883e'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.moveTo(x, 0)
      ctx.lineTo(x, h)
      ctx.stroke()
      ctx.setLineDash([])
    }
  }

  // Value label
  const latest = values[values.length - 1]
  ctx.fillStyle = '#8b949e'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'right'
  ctx.fillText(latest.toFixed(2), w - 4, 12)
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
