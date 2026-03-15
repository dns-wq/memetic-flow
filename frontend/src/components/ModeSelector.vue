<template>
  <div class="mode-selector">
    <h3 class="section-title">Simulation Mode</h3>
    <div class="mode-grid">
      <div v-for="mode in modes" :key="mode.name" class="mode-card"
           :class="{ active: selected === mode.name }"
           @click="select(mode.name)">
        <div class="mode-icon">{{ iconMap[mode.icon] || '?' }}</div>
        <div class="mode-info">
          <div class="mode-name">{{ formatName(mode.name) }}</div>
          <div class="mode-desc">{{ mode.description }}</div>
        </div>
        <div v-if="mode.metrics_focus.length" class="mode-metrics">
          <span v-for="m in mode.metrics_focus.slice(0, 3)" :key="m" class="metric-tag">
            {{ m.replace(/_/g, ' ') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modes: { type: Array, default: () => [] },
})

const emit = defineEmits(['select'])

const selected = ref(null)

const iconMap = {
  wrench: 'W',
  castle: 'C',
  brain: 'B',
  atom: 'A',
}

function formatName(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function select(name) {
  selected.value = name
  emit('select', name)
}
</script>

<style scoped>
.mode-selector {
  padding: 12px;
  background: #161b22;
  border-radius: 8px;
}
.section-title {
  margin: 0 0 10px;
  color: #e6edf3;
  font-size: 14px;
  font-weight: 600;
}
.mode-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.mode-card {
  background: #0d1117;
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.15s;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.mode-card:hover { border-color: #30363d; }
.mode-card.active { border-color: #58a6ff; background: #0d1117; }
.mode-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #21262d;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #58a6ff;
  flex-shrink: 0;
}
.mode-info { flex: 1; min-width: 0; }
.mode-name {
  font-size: 13px;
  font-weight: 600;
  color: #e6edf3;
}
.mode-desc {
  font-size: 11px;
  color: #8b949e;
  margin-top: 2px;
  line-height: 1.4;
}
.mode-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.metric-tag {
  font-size: 10px;
  background: #21262d;
  color: #8b949e;
  padding: 1px 6px;
  border-radius: 8px;
}
</style>
