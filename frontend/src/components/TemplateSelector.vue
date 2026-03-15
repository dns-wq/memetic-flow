<template>
  <div class="template-selector">
    <h3 class="section-title">Dynamics Templates</h3>
    <div v-for="tmpl in templates" :key="tmpl.name" class="template-card"
         :class="{ active: selected.includes(tmpl.name) }"
         @click="toggle(tmpl.name)">
      <div class="card-header">
        <span class="card-name">{{ tmpl.name }}</span>
        <span class="card-check">{{ selected.includes(tmpl.name) ? '✓' : '' }}</span>
      </div>
      <div class="card-desc">{{ tmpl.description }}</div>
      <div v-if="selected.includes(tmpl.name)" class="params-section">
        <div v-for="(spec, pname) in tmpl.parameters" :key="pname" class="param-row">
          <label class="param-label" :title="spec.description">{{ pname }}</label>
          <input type="range" class="param-slider"
                 :min="spec.min" :max="spec.max" :step="(spec.max - spec.min) / 100"
                 :value="paramValues[tmpl.name]?.[pname] ?? spec.default"
                 @input="onParamChange(tmpl.name, pname, $event)" />
          <span class="param-value">{{ (paramValues[tmpl.name]?.[pname] ?? spec.default).toFixed(3) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  templates: { type: Array, default: () => [] },
  suggested: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:selected', 'update:params'])

const selected = ref([...props.suggested])
const paramValues = ref({})

function toggle(name) {
  const idx = selected.value.indexOf(name)
  if (idx >= 0) selected.value.splice(idx, 1)
  else selected.value.push(name)
  emit('update:selected', [...selected.value])
}

function onParamChange(tmplName, pname, e) {
  if (!paramValues.value[tmplName]) paramValues.value[tmplName] = {}
  paramValues.value[tmplName][pname] = parseFloat(e.target.value)
  emit('update:params', { ...paramValues.value })
}

watch(() => props.suggested, (v) => {
  if (v.length && !selected.value.length) {
    selected.value = [...v]
    emit('update:selected', [...selected.value])
  }
})
</script>

<style scoped>
.template-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #161b22;
  border-radius: 8px;
  overflow-y: auto;
}
.section-title {
  margin: 0 0 4px;
  color: #e6edf3;
  font-size: 14px;
  font-weight: 600;
}
.template-card {
  background: #0d1117;
  border: 1px solid #21262d;
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.template-card.active {
  border-color: #58a6ff;
}
.template-card:hover { border-color: #30363d; }
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-name {
  font-size: 13px;
  font-weight: 600;
  color: #e6edf3;
  text-transform: capitalize;
}
.card-check {
  color: #58a6ff;
  font-size: 14px;
}
.card-desc {
  font-size: 11px;
  color: #8b949e;
  margin-top: 2px;
}
.params-section {
  margin-top: 8px;
  border-top: 1px solid #21262d;
  padding-top: 6px;
}
.param-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.param-label {
  font-size: 11px;
  color: #8b949e;
  min-width: 90px;
  cursor: help;
}
.param-slider {
  flex: 1;
  accent-color: #58a6ff;
}
.param-value {
  font-size: 11px;
  color: #e6edf3;
  min-width: 42px;
  text-align: right;
  font-family: monospace;
}
</style>
