<template>
  <div class="demo-player">
    <!-- Loading -->
    <div v-if="loading" class="center-state">
      <div class="spinner"></div>
      <p>Loading {{ scenario }} scenario...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="center-state error">
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="load">Retry</button>
    </div>

    <!-- Main content -->
    <template v-else>
      <!-- Header -->
      <header class="dp-header">
        <div class="header-left">
          <router-link to="/" class="brand">Memetic Flow</router-link>
          <span class="separator">/</span>
          <span class="demo-badge">DEMO</span>
          <span class="demo-title">{{ metadata.title }}</span>
        </div>
        <div class="header-right">
          <span class="demo-stats">
            {{ metadata.num_nodes }} nodes &middot; {{ metadata.num_edges }} edges &middot; {{ metadata.total_steps }} steps
          </span>
          <span class="mode-badge">{{ metadata.mode }}</span>
          <!-- Scenario switcher -->
          <select class="scenario-select" :value="scenario" @change="switchScenario($event.target.value)">
            <option v-for="s in scenarios" :key="s.name" :value="s.name">{{ s.title }}</option>
          </select>
        </div>
      </header>

      <!-- Body -->
      <div class="dp-body">
        <div class="left-panel">
          <DynamicsGraphPanel :snapshot="currentSnapshot" class="graph-area" />
          <TemporalSlider v-model="currentTimestep" :maxTimestep="maxTimestep"
                          :events="events" class="timeline-area" />
        </div>
        <div class="right-panel">
          <!-- Tabs -->
          <div class="rp-tabs">
            <button :class="['rp-tab', { active: activeTab === 'overview' }]"
                    @click="activeTab = 'overview'">Overview</button>
            <button :class="['rp-tab', { active: activeTab === 'document' }]"
                    @click="activeTab = 'document'">
              Source Document
            </button>
          </div>

          <!-- Overview tab -->
          <template v-if="activeTab === 'overview'">
            <div class="scenario-info">
              <h3>{{ metadata.title }}</h3>
              <p class="source">Source: {{ metadata.source }}</p>
              <p class="description">{{ metadata.description }}</p>
            </div>
            <MetricsDashboard :metrics="metrics" :currentTimestep="currentTimestep"
                              :events="events" />
          </template>

          <!-- Document tab -->
          <template v-if="activeTab === 'document'">
            <div class="document-viewer" v-if="documentContent">
              <div class="doc-header">
                <span class="doc-filename">{{ metadata.document || 'source.md' }}</span>
                <a v-if="metadata.source_url" :href="metadata.source_url"
                   target="_blank" rel="noopener" class="doc-source-link">
                  View original &rarr;
                </a>
              </div>
              <div class="doc-body" v-html="renderedDocument"></div>
            </div>
            <div v-else class="doc-empty">
              <p>No source document available for this scenario.</p>
            </div>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import DynamicsGraphPanel from '@components/DynamicsGraphPanel.vue'
import TemporalSlider from '@components/TemporalSlider.vue'
import MetricsDashboard from '@components/MetricsDashboard.vue'
import { loadManifest, loadScenarioData, loadDocument, getSnapshot } from '../data/staticLoader.js'

const props = defineProps({ scenario: String })
const router = useRouter()
const route = useRoute()

const loading = ref(true)
const error = ref(null)
const metadata = ref({})
const currentSnapshot = ref(null)
const currentTimestep = ref(0)
const maxTimestep = ref(0)
const metrics = ref({})
const events = ref([])
const scenarios = ref([])
const activeTab = ref('overview')
const documentContent = ref(null)

/** Simple markdown to HTML renderer (no external dependency) */
function renderMarkdown(md) {
  if (!md) return ''
  return md
    // Escape HTML
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Headers
    .replace(/^### (.+)$/gm, '<h5>$1</h5>')
    .replace(/^## (.+)$/gm, '<h4>$1</h4>')
    .replace(/^# (.+)$/gm, '<h3>$1</h3>')
    // Bold and italic
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    // List items
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
    // Paragraphs (double newline)
    .replace(/\n\n/g, '</p><p>')
    // Single newlines within paragraphs
    .replace(/\n/g, '<br/>')
    // Wrap in paragraph
    .replace(/^/, '<p>').replace(/$/, '</p>')
    // Clean up empty paragraphs
    .replace(/<p><\/p>/g, '')
    .replace(/<p>(<h[345]>)/g, '$1')
    .replace(/(<\/h[345]>)<\/p>/g, '$1')
    .replace(/<p>(<ul>)/g, '$1')
    .replace(/(<\/ul>)<\/p>/g, '$1')
}

const renderedDocument = computed(() => renderMarkdown(documentContent.value))

onMounted(() => load())

async function load() {
  loading.value = true
  error.value = null
  try {
    // Load manifest for scenario switcher
    const manifest = await loadManifest()
    scenarios.value = manifest.scenarios

    // Load scenario data + document in parallel
    const scenarioName = props.scenario || route.params.scenario
    const [data, doc] = await Promise.all([
      loadScenarioData(scenarioName),
      loadDocument(scenarioName),
    ])

    metadata.value = data.metadata
    currentSnapshot.value = data.graph
    metrics.value = data.metrics
    events.value = Array.isArray(data.events) ? data.events : []
    maxTimestep.value = data.metadata.total_steps || 0
    currentTimestep.value = maxTimestep.value
    documentContent.value = doc
    activeTab.value = 'overview'

    loading.value = false
  } catch (e) {
    error.value = e.message || 'Failed to load scenario'
    loading.value = false
  }
}

function switchScenario(name) {
  router.push({ name: 'Demo', params: { scenario: name } })
}

// Reload on route change
watch(() => route.params.scenario, (newVal) => {
  if (newVal) load()
})

// Load snapshot when timeline changes
watch(currentTimestep, async (ts) => {
  const scenarioName = props.scenario || route.params.scenario
  try {
    const snap = await getSnapshot(scenarioName, ts)
    if (snap) currentSnapshot.value = snap
  } catch (_) { /* ignore */ }
})
</script>

<style scoped>
.demo-player {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

.center-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: 16px;
}
.center-state.error { color: #f85149; }

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #21262d;
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.dp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: #161b22;
  border-bottom: 1px solid #21262d;
  flex-shrink: 0;
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
  text-decoration: none;
}
.brand:hover { text-decoration: underline; }
.separator { color: #484f58; }
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
  max-width: 300px;
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
.scenario-select {
  background: #21262d;
  color: #c9d1d9;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
}
.scenario-select:hover { border-color: #58a6ff; }

.dp-body {
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

.rp-tabs {
  display: flex;
  gap: 0;
  flex-shrink: 0;
  border-bottom: 1px solid #21262d;
  margin-bottom: 8px;
}
.rp-tab {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #8b949e;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.rp-tab:hover { color: #c9d1d9; }
.rp-tab.active {
  color: #58a6ff;
  border-bottom-color: #58a6ff;
}

.scenario-info {
  padding: 12px;
  background: #161b22;
  border-radius: 8px;
  border: 1px solid #21262d;
}
.scenario-info h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #e6edf3;
}
.scenario-info .source {
  font-size: 11px;
  color: #8b949e;
  margin-bottom: 8px;
}
.scenario-info .description {
  font-size: 12px;
  color: #c9d1d9;
  line-height: 1.5;
}

/* Document viewer */
.document-viewer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  background: #161b22;
  border-radius: 8px;
  border: 1px solid #21262d;
  overflow: hidden;
}
.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #1c2128;
  border-bottom: 1px solid #21262d;
  flex-shrink: 0;
}
.doc-filename {
  font-size: 12px;
  color: #8b949e;
  font-family: monospace;
}
.doc-source-link {
  font-size: 11px;
  color: #58a6ff;
  text-decoration: none;
}
.doc-source-link:hover { text-decoration: underline; }
.doc-body {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
  font-size: 13px;
  line-height: 1.7;
  color: #c9d1d9;
}
.doc-body h3 {
  font-size: 16px;
  color: #e6edf3;
  margin: 20px 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #21262d;
}
.doc-body h4 {
  font-size: 14px;
  color: #e6edf3;
  margin: 16px 0 6px 0;
}
.doc-body h5 {
  font-size: 13px;
  color: #e6edf3;
  margin: 12px 0 4px 0;
}
.doc-body ul {
  padding-left: 20px;
  margin: 8px 0;
}
.doc-body li {
  margin-bottom: 4px;
}
.doc-body a {
  color: #58a6ff;
  text-decoration: none;
}
.doc-body a:hover { text-decoration: underline; }
.doc-body strong { color: #e6edf3; }
.doc-empty {
  padding: 24px;
  text-align: center;
  color: #8b949e;
  font-size: 13px;
}

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

@media (max-width: 768px) {
  .dp-body { flex-direction: column; }
  .right-panel {
    max-width: none;
    border-left: none;
    border-top: 1px solid #21262d;
  }
  .left-panel { min-height: 50vh; }
  .header-left .demo-title { display: none; }
  .demo-stats { display: none; }
}
</style>
