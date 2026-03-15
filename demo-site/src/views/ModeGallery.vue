<template>
  <div class="mode-gallery">
    <header class="mg-header">
      <router-link to="/" class="brand">Memetic Flow</router-link>
      <span class="separator">/</span>
      <span class="view-name">Simulation Modes</span>
    </header>

    <div class="mg-content">
      <h1>8 Simulation Modes</h1>
      <p class="mg-sub">Each mode is a curated bundle of dynamical templates, metrics, and visualization presets for a specific domain.</p>

      <div class="modes-list">
        <div v-for="mode in modes" :key="mode.name" class="mode-detail"
             :style="{ '--mode-color': modeColor(mode.name) }">
          <div class="md-header">
            <h2>{{ formatMode(mode.name) }}</h2>
            <span class="md-badge">{{ mode.name }}</span>
          </div>
          <p class="md-desc">{{ mode.description }}</p>
          <div class="md-templates" v-if="mode.templates">
            <span class="md-label">Templates:</span>
            <span v-for="t in mode.templates" :key="t" class="md-tag">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { MODE_DEFINITIONS, MODE_COLORS } from '../data/modes.js'

const modes = MODE_DEFINITIONS

function modeColor(name) {
  return MODE_COLORS[name] || '#8b949e'
}

function formatMode(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
</script>

<style scoped>
.mode-gallery {
  min-height: 100vh;
  background: #0d1117;
  color: #e6edf3;
}

.mg-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #161b22;
  border-bottom: 1px solid #21262d;
}
.brand {
  font-weight: 700;
  font-size: 16px;
  color: #58a6ff;
  text-decoration: none;
}
.brand:hover { text-decoration: underline; }
.separator { color: #484f58; }
.view-name { font-size: 14px; color: #8b949e; }

.mg-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
}
.mg-content h1 {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}
.mg-sub {
  font-size: 15px;
  color: #8b949e;
  margin-bottom: 40px;
}

.modes-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mode-detail {
  padding: 24px;
  background: #161b22;
  border: 1px solid #21262d;
  border-left: 4px solid var(--mode-color);
  border-radius: 8px;
}
.md-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.md-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--mode-color);
}
.md-badge {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 6px;
  background: #21262d;
  border-radius: 4px;
  color: #8b949e;
}
.md-desc {
  font-size: 14px;
  color: #c9d1d9;
  line-height: 1.6;
  margin-bottom: 12px;
}
.md-templates {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.md-label {
  font-size: 11px;
  color: #8b949e;
  font-weight: 600;
}
.md-tag {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 8px;
  background: #21262d;
  border-radius: 4px;
  color: #c9d1d9;
}
</style>
