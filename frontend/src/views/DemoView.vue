<template>
  <div class="demo-view">
    <!-- Loading state -->
    <div v-if="loading" class="demo-loading">
      <div class="spinner"></div>
      <p>Loading {{ demoName }} demo...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="demo-error">
      <p>Failed to load demo: {{ error }}</p>
      <button class="btn btn-primary" @click="loadDemoData">Retry</button>
    </div>

    <!-- Demo header + DynamicsView content -->
    <template v-else>
      <header class="demo-header">
        <div class="header-left">
          <span class="brand">Memetic Flow</span>
          <span class="separator">/</span>
          <span class="demo-badge">DEMO</span>
          <span class="demo-title">{{ demoMeta.description || demoName }}</span>
        </div>
        <div class="header-right">
          <span class="demo-stats">
            {{ demoMeta.num_nodes }} nodes &middot; {{ demoMeta.num_edges }} edges &middot; {{ demoMeta.steps }} steps
          </span>
          <span class="mode-badge">{{ demoMeta.mode }}</span>
          <span class="status-badge completed">completed</span>
        </div>
      </header>

      <div class="dv-body">
        <!-- Left: Graph panel + timeline -->
        <div class="left-panel">
          <DynamicsGraphPanel :snapshot="currentSnapshot" class="graph-area" />
          <TemporalSlider v-model="currentTimestep" :maxTimestep="maxTimestep"
                          :events="events" class="timeline-area" />
        </div>

        <!-- Right: Metrics -->
        <div class="right-panel">
          <MetricsDashboard :metrics="metricSeries" :currentTimestep="currentTimestep"
                            :events="events" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import DynamicsGraphPanel from '../components/DynamicsGraphPanel.vue'
import TemporalSlider from '../components/TemporalSlider.vue'
import MetricsDashboard from '../components/MetricsDashboard.vue'
import {
  loadDemo, getGraph, getSnapshot, getMetrics, getEvents,
} from '../api/dynamics'

const route = useRoute()
const demoName = route.params.demoName

const loading = ref(true)
const error = ref(null)
const simId = ref(null)
const demoMeta = ref({})
const currentTimestep = ref(0)
const maxTimestep = ref(0)
const currentSnapshot = ref(null)
const metricSeries = ref({})
const events = ref([])

onMounted(() => {
  loadDemoData()
})

async function loadDemoData() {
  loading.value = true
  error.value = null
  try {
    // Load demo into backend (interceptor returns response.data directly)
    const data = await loadDemo(demoName)
    simId.value = data.sim_id
    demoMeta.value = data
    maxTimestep.value = data.steps || 0

    // Load graph, metrics, events
    const [graphData, metricsData, eventsData] = await Promise.all([
      getGraph(simId.value),
      getMetrics(simId.value),
      getEvents(simId.value),
    ])

    currentSnapshot.value = graphData
    metricSeries.value = metricsData
    events.value = eventsData

    // Start at final timestep to show completed state
    currentTimestep.value = maxTimestep.value

    loading.value = false
  } catch (e) {
    error.value = e.message || 'Unknown error'
    loading.value = false
  }
}

// Watch timestep changes to load historical snapshot
watch(currentTimestep, async (ts) => {
  if (!simId.value) return
  try {
    const snap = await getSnapshot(simId.value, ts)
    currentSnapshot.value = snap
  } catch (e) {
    // Snapshot may not exist for every timestep (sampled every 5 steps)
    const nearest = Math.floor(ts / 5) * 5
    if (nearest !== ts) {
      try {
        const snap = await getSnapshot(simId.value, nearest)
        currentSnapshot.value = snap
      } catch (_) { /* ignore */ }
    }
  }
})
</script>

<style scoped>
.demo-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

.demo-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 16px;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #21262d;
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.demo-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 16px;
  color: #f85149;
}

.demo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: #161b22;
  border-bottom: 1px solid #21262d;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.brand {
  font-weight: 700;
  font-size: 16px;
  color: #58a6ff;
}
.separator {
  color: #484f58;
}
.demo-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #da3633;
  color: #fff;
  font-weight: 700;
  letter-spacing: 1px;
}
.demo-title {
  font-size: 13px;
  color: #c9d1d9;
  max-width: 400px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.demo-stats {
  font-size: 12px;
  color: #8b949e;
}
.mode-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #1f3a5f;
  color: #58a6ff;
  font-weight: 600;
}
.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.status-badge.completed { background: #272d1f; color: #a3be8c; }

.btn {
  padding: 5px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary { background: #238636; color: #fff; }
.btn-primary:hover { background: #2ea043; }

.dv-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.left-panel {
  flex: 2;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.graph-area {
  flex: 1;
  min-height: 0;
}
.timeline-area {
  flex-shrink: 0;
}
.right-panel {
  flex: 1;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
  overflow-y: auto;
  border-left: 1px solid #21262d;
}
</style>
