<template>
  <div class="dynamics-view">
    <!-- Header -->
    <header class="dv-header">
      <div class="header-left">
        <span class="brand">Memetic Flow</span>
        <span class="separator">/</span>
        <span class="view-name">Dynamics Simulation</span>
      </div>
      <div class="header-right">
        <span v-if="status" class="status-badge" :class="status">{{ status }}</span>
        <button v-if="status === 'configured' || status === 'completed' || status === 'stopped'"
                class="btn btn-primary" @click="startSim">
          {{ status === 'configured' ? 'Start' : 'Restart' }}
        </button>
        <button v-if="status === 'running'" class="btn btn-danger" @click="stopSim">Stop</button>
        <div v-if="status === 'completed'" class="export-group">
          <button class="btn btn-secondary" @click="downloadJSON">Export JSON</button>
          <button class="btn btn-secondary" @click="downloadCSV">Export CSV</button>
        </div>
      </div>
    </header>

    <!-- Main layout -->
    <div class="dv-body">
      <!-- Left: Graph panel + timeline -->
      <div class="left-panel">
        <DynamicsGraphPanel :snapshot="currentSnapshot" class="graph-area" />
        <TemporalSlider v-model="currentTimestep" :maxTimestep="maxTimestep"
                        :events="events" class="timeline-area" />
      </div>

      <!-- Right: Controls + metrics -->
      <div class="right-panel">
        <ModeSelector :modes="modeDefs" @select="onModeSelected" />
        <TemplateSelector :templates="templateDefs" :suggested="suggestedTemplates"
                          @update:selected="onTemplatesChanged"
                          @update:params="onParamsChanged" />
        <MetricsDashboard :metrics="metricSeries" :currentTimestep="currentTimestep"
                          :events="events" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import DynamicsGraphPanel from '../components/DynamicsGraphPanel.vue'
import TemporalSlider from '../components/TemporalSlider.vue'
import TemplateSelector from '../components/TemplateSelector.vue'
import MetricsDashboard from '../components/MetricsDashboard.vue'
import ModeSelector from '../components/ModeSelector.vue'
import {
  initializeDynamics, getGraph, getSnapshot,
  listTemplates, configureDynamics,
  startDynamics, stopDynamics, getDynamicsStatus,
  getMetrics, getEvents,
  exportJSON, exportCSV,
  listModes, applyMode,
} from '../api/dynamics'

const route = useRoute()

// --- State ---
const simId = ref(route.params.simId || null)
const status = ref(null)
const currentTimestep = ref(0)
const maxTimestep = ref(0)
const currentSnapshot = ref(null)
const templateDefs = ref([])
const suggestedTemplates = ref([])
const selectedTemplates = ref([])
const templateParams = ref({})
const metricSeries = ref({})
const events = ref([])
const modeDefs = ref([])

let pollTimer = null

// --- Lifecycle ---
onMounted(async () => {
  // Load template definitions and modes in parallel
  // Note: axios interceptor already unwraps response.data
  try {
    const [tmplData, modeData] = await Promise.all([
      listTemplates(),
      listModes(),
    ])
    templateDefs.value = tmplData
    modeDefs.value = modeData
  } catch (e) {
    console.error('Failed to load templates', e)
  }

  // If simId was provided via route, load existing state
  if (simId.value) {
    await refreshStatus()
    await loadGraph()
    await loadMetrics()
    await loadEvents()
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// --- Actions ---
async function onModeSelected(modeName) {
  if (!simId.value) return
  try {
    const data = await applyMode(simId.value, modeName)
    status.value = data.status
    suggestedTemplates.value = data.templates || []
    selectedTemplates.value = data.templates || []
    await loadGraph()
  } catch (e) {
    console.error('Apply mode failed', e)
  }
}

async function onTemplatesChanged(templates) {
  selectedTemplates.value = templates
  if (!simId.value) return
  try {
    await configureDynamics(simId.value, templates, templateParams.value)
    status.value = 'configured'
  } catch (e) {
    console.error('Configure failed', e)
  }
}

function onParamsChanged(params) {
  templateParams.value = params
  // Re-configure if already configured
  if (simId.value && selectedTemplates.value.length) {
    configureDynamics(simId.value, selectedTemplates.value, params).catch(console.error)
  }
}

async function startSim() {
  if (!simId.value) return
  try {
    await startDynamics(simId.value, 200)
    status.value = 'running'
    startPolling()
  } catch (e) {
    console.error('Start failed', e)
  }
}

async function stopSim() {
  if (!simId.value) return
  try {
    await stopDynamics(simId.value)
    status.value = 'stopped'
    stopPolling()
  } catch (e) {
    console.error('Stop failed', e)
  }
}

// --- Export ---
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function downloadJSON() {
  if (!simId.value) return
  try {
    const resp = await exportJSON(simId.value)
    triggerDownload(resp.data, `simulation_${simId.value}.json`)
  } catch (e) { console.error('Export JSON failed', e) }
}

async function downloadCSV() {
  if (!simId.value) return
  try {
    const resp = await exportCSV(simId.value)
    triggerDownload(resp.data, `metrics_${simId.value}.csv`)
  } catch (e) { console.error('Export CSV failed', e) }
}

// --- Polling ---
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    await refreshStatus()
    await loadMetrics()
    await loadEvents()
    if (status.value !== 'running') stopPolling()
  }, 1000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function refreshStatus() {
  if (!simId.value) return
  try {
    const data = await getDynamicsStatus(simId.value)
    status.value = data.status
    maxTimestep.value = data.timestep || 0
    if (status.value === 'running') {
      currentTimestep.value = maxTimestep.value
    }
  } catch (e) { /* ignore */ }
}

async function loadGraph() {
  if (!simId.value) return
  try {
    currentSnapshot.value = await getGraph(simId.value)
  } catch (e) { /* ignore */ }
}

async function loadMetrics() {
  if (!simId.value) return
  try {
    metricSeries.value = await getMetrics(simId.value)
  } catch (e) { /* ignore */ }
}

async function loadEvents() {
  if (!simId.value) return
  try {
    events.value = await getEvents(simId.value)
  } catch (e) { /* ignore */ }
}

// --- Watch timestep changes to load historical snapshot ---
watch(currentTimestep, async (ts) => {
  if (!simId.value || ts === maxTimestep.value) {
    // Show live graph at latest timestep
    await loadGraph()
    return
  }
  try {
    currentSnapshot.value = await getSnapshot(simId.value, ts)
  } catch (e) { /* ignore */ }
})

// --- Public method for external initialization ---
async function initFromGraphData(graphData, ontology = null) {
  try {
    const data = await initializeDynamics(graphData, ontology)
    simId.value = data.sim_id
    suggestedTemplates.value = data.suggested_templates || []
    status.value = 'initialized'
    await loadGraph()
  } catch (e) {
    console.error('Init failed', e)
  }
}

defineExpose({ initFromGraphData })
</script>

<style scoped>
.dynamics-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

.dv-header {
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
.view-name {
  font-size: 14px;
  color: #8b949e;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.status-badge.initialized { background: #21262d; color: #8b949e; }
.status-badge.configured { background: #1f3a5f; color: #58a6ff; }
.status-badge.running { background: #1a4731; color: #3fb950; }
.status-badge.completed { background: #272d1f; color: #a3be8c; }
.status-badge.stopped { background: #3d1f1f; color: #f85149; }
.status-badge.error { background: #3d1f1f; color: #f85149; }

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
.btn-danger { background: #da3633; color: #fff; }
.btn-danger:hover { background: #f85149; }
.btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
.btn-secondary:hover { background: #30363d; }

.export-group {
  display: flex;
  gap: 6px;
}

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
