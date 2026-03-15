<template>
  <div class="landing">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg">
        <canvas ref="heroCanvas"></canvas>
      </div>
      <div class="hero-content">
        <h1 class="hero-title">Memetic Flow</h1>
        <p class="hero-tagline">A physics engine for ideas.</p>
        <p class="hero-sub">
          Upload any document. Extract entities and relationships.
          Watch complex systems emerge through dynamical simulation.
        </p>
        <div class="hero-actions">
          <router-link v-if="firstScenario" :to="{ name: 'Demo', params: { scenario: firstScenario } }" class="btn btn-primary btn-lg">
            Try a Demo
          </router-link>
          <a href="https://github.com/memeticflow/memetic-flow" target="_blank" class="btn btn-secondary btn-lg">
            View on GitHub
          </a>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="features">
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4m-2.636-7.364l-2.828 2.828m-5.656 5.656l-2.828 2.828m11.312 0l-2.828-2.828M7.05 7.05 4.222 4.222"/></svg>
          </div>
          <h3>Typed Knowledge Graphs</h3>
          <p>Agents, institutions, ideas, and resources — each with evolving state vectors and directed relationships.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="m7 16 4-8 4 5 4-10"/></svg>
          </div>
          <h3>Template Dynamics</h3>
          <p>Diffusion, opinion formation, resource competition, and feedback loops — grounded in complexity science.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-5"/></svg>
          </div>
          <h3>Real-Time Metrics</h3>
          <p>Entropy, polarization, clustering, Gini coefficients — automatically computed at each timestep.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8m-4-4v4"/></svg>
          </div>
          <h3>D3.js Force Visualization</h3>
          <p>Canvas-rendered force graph with animated flows, institutional clustering, and temporal replay.</p>
        </div>
      </div>
    </section>

    <!-- Scenarios -->
    <section class="scenarios" v-if="scenarios.length">
      <h2 class="section-title">Live Demos</h2>
      <p class="section-sub">Real documents, real entities, real dynamics. No synthetic data.</p>
      <div class="scenario-grid">
        <router-link v-for="s in scenarios" :key="s.name"
                     :to="{ name: 'Demo', params: { scenario: s.name } }"
                     class="scenario-card">
          <div class="sc-mode" :style="{ color: modeColor(s.mode) }">{{ s.mode }}</div>
          <h3 class="sc-title">{{ s.title }}</h3>
          <p class="sc-desc">{{ s.description }}</p>
          <div class="sc-stats">
            <span>{{ s.num_nodes }} nodes</span>
            <span>{{ s.num_edges }} edges</span>
            <span>{{ s.total_steps }} steps</span>
          </div>
        </router-link>
      </div>
    </section>

    <!-- Modes -->
    <section class="modes-section">
      <h2 class="section-title">8 Simulation Modes</h2>
      <p class="section-sub">Each mode bundles templates, metrics, and visualization presets for a specific domain.</p>
      <div class="modes-grid">
        <div v-for="mode in modes" :key="mode.name" class="mode-card"
             :style="{ borderColor: modeColor(mode.name) }">
          <div class="mc-name" :style="{ color: modeColor(mode.name) }">{{ formatMode(mode.name) }}</div>
          <p class="mc-desc">{{ mode.description }}</p>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta">
      <h2>Start Simulating</h2>
      <p>Clone the repo, upload a document, and watch complexity emerge.</p>
      <div class="cta-actions">
        <a href="https://github.com/memeticflow/memetic-flow" target="_blank" class="btn btn-primary btn-lg">
          Get Started
        </a>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <p>Built on <a href="https://github.com/666ghj/MiroFish" target="_blank">MiroFish</a>. Licensed AGPL-3.0.</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'
import { loadManifest } from '../data/staticLoader.js'
import { MODE_DEFINITIONS, MODE_COLORS } from '../data/modes.js'

const scenarios = ref([])
const modes = MODE_DEFINITIONS
const heroCanvas = ref(null)
let animFrame = null

const firstScenario = computed(() => scenarios.value[0]?.name)

function modeColor(name) {
  return MODE_COLORS[name] || '#8b949e'
}

function formatMode(name) {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

onMounted(async () => {
  try {
    const manifest = await loadManifest()
    scenarios.value = manifest.scenarios
  } catch (_) { /* demo site may be previewing without data */ }

  initHeroAnimation()
})

onUnmounted(() => {
  if (animFrame) cancelAnimationFrame(animFrame)
})

function initHeroAnimation() {
  const canvas = heroCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1

  function resize() {
    const rect = canvas.parentElement.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    canvas.style.width = rect.width + 'px'
    canvas.style.height = rect.height + 'px'
    ctx.scale(dpr, dpr)
  }
  resize()
  window.addEventListener('resize', resize)

  // Generate random nodes
  const w = canvas.parentElement.clientWidth
  const h = canvas.parentElement.clientHeight
  const nodeCount = 60
  const nodes = Array.from({ length: nodeCount }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.3,
    vy: (Math.random() - 0.5) * 0.3,
    r: 2 + Math.random() * 3,
    color: ['#58a6ff', '#3fb950', '#f0883e', '#d2a8ff', '#f85149'][Math.floor(Math.random() * 5)],
  }))

  // Generate edges
  const edges = []
  for (let i = 0; i < nodeCount; i++) {
    const count = 1 + Math.floor(Math.random() * 2)
    for (let c = 0; c < count; c++) {
      const j = Math.floor(Math.random() * nodeCount)
      if (j !== i) edges.push([i, j])
    }
  }

  function draw() {
    const cw = canvas.parentElement.clientWidth
    const ch = canvas.parentElement.clientHeight
    ctx.clearRect(0, 0, cw, ch)

    // Draw edges
    ctx.globalAlpha = 0.08
    ctx.strokeStyle = '#58a6ff'
    ctx.lineWidth = 0.5
    for (const [i, j] of edges) {
      const a = nodes[i], b = nodes[j]
      const dist = Math.hypot(a.x - b.x, a.y - b.y)
      if (dist < 200) {
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }
    }

    // Draw nodes
    ctx.globalAlpha = 0.4
    for (const n of nodes) {
      ctx.fillStyle = n.color
      ctx.beginPath()
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2)
      ctx.fill()

      // Update position
      n.x += n.vx
      n.y += n.vy
      if (n.x < 0 || n.x > cw) n.vx *= -1
      if (n.y < 0 || n.y > ch) n.vy *= -1
    }

    ctx.globalAlpha = 1
    animFrame = requestAnimationFrame(draw)
  }
  draw()
}
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background: #0d1117;
}

/* Hero */
.hero {
  position: relative;
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}
.hero-bg canvas {
  width: 100%;
  height: 100%;
}
.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 40px 20px;
}
.hero-title {
  font-size: 56px;
  font-weight: 800;
  background: linear-gradient(135deg, #58a6ff 0%, #d2a8ff 50%, #f0883e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}
.hero-tagline {
  font-size: 24px;
  color: #c9d1d9;
  font-weight: 500;
  margin-bottom: 16px;
}
.hero-sub {
  font-size: 16px;
  color: #8b949e;
  max-width: 560px;
  margin: 0 auto 32px;
  line-height: 1.6;
}
.hero-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.btn-lg { padding: 12px 24px; font-size: 16px; }
.btn-primary { background: #238636; color: #fff; }
.btn-primary:hover { background: #2ea043; }
.btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
.btn-secondary:hover { background: #30363d; }

/* Features */
.features {
  padding: 80px 20px;
  max-width: 1100px;
  margin: 0 auto;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
}
.feature-card {
  padding: 24px;
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 12px;
  transition: border-color 0.2s;
}
.feature-card:hover { border-color: #30363d; }
.feature-icon {
  width: 40px;
  height: 40px;
  color: #58a6ff;
  margin-bottom: 12px;
}
.feature-icon svg { width: 100%; height: 100%; }
.feature-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}
.feature-card p {
  font-size: 13px;
  color: #8b949e;
  line-height: 1.5;
}

/* Scenarios */
.scenarios {
  padding: 60px 20px 80px;
  max-width: 1100px;
  margin: 0 auto;
}
.section-title {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 8px;
}
.section-sub {
  font-size: 15px;
  color: #8b949e;
  text-align: center;
  margin-bottom: 40px;
}
.scenario-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}
.scenario-card {
  display: block;
  padding: 24px;
  background: #161b22;
  border: 1px solid #21262d;
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}
.scenario-card:hover {
  border-color: #58a6ff;
  transform: translateY(-2px);
}
.sc-mode {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.sc-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #e6edf3;
}
.sc-desc {
  font-size: 13px;
  color: #8b949e;
  line-height: 1.5;
  margin-bottom: 12px;
}
.sc-stats {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: #484f58;
  font-family: 'JetBrains Mono', monospace;
}

/* Modes */
.modes-section {
  padding: 60px 20px 80px;
  max-width: 1100px;
  margin: 0 auto;
}
.modes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.mode-card {
  padding: 16px;
  background: #161b22;
  border: 1px solid #21262d;
  border-left: 3px solid;
  border-radius: 8px;
}
.mc-name {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 6px;
}
.mc-desc {
  font-size: 12px;
  color: #8b949e;
  line-height: 1.5;
}

/* CTA */
.cta {
  text-align: center;
  padding: 80px 20px;
  background: linear-gradient(180deg, transparent, #161b22);
}
.cta h2 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}
.cta p {
  font-size: 15px;
  color: #8b949e;
  margin-bottom: 24px;
}
.cta-actions {
  display: flex;
  justify-content: center;
}

/* Footer */
.footer {
  text-align: center;
  padding: 24px;
  border-top: 1px solid #21262d;
  font-size: 12px;
  color: #484f58;
}
.footer a { color: #58a6ff; text-decoration: none; }
.footer a:hover { text-decoration: underline; }

@media (max-width: 768px) {
  .hero-title { font-size: 36px; }
  .hero-tagline { font-size: 18px; }
  .hero-actions { flex-direction: column; align-items: center; }
  .scenario-grid { grid-template-columns: 1fr; }
}
</style>
