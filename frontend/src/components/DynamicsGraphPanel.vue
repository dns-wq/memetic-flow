<template>
  <div class="dynamics-graph-panel" ref="containerRef">
    <canvas ref="canvasRef" @wheel.prevent="onWheel" @mousedown="onMouseDown"
            @mousemove="onMouseMove" @mouseup="onMouseUp" @dblclick="onDblClick" />
    <div v-if="hoveredNode" class="tooltip" :style="tooltipStyle">
      <div class="tooltip-label">{{ hoveredNode.label }}</div>
      <div class="tooltip-type">{{ hoveredNode.node_type }}</div>
      <div v-if="hoveredNode.metadata?.description" class="tooltip-desc">
        {{ hoveredNode.metadata.description }}
      </div>
      <div v-if="hoveredNode.metadata?.role" class="tooltip-field">
        <span class="field-label">Role:</span> {{ hoveredNode.metadata.role }}
      </div>
      <div v-if="hoveredNode.metadata?.goals" class="tooltip-field">
        <span class="field-label">Goals:</span> {{ hoveredNode.metadata.goals }}
      </div>
      <div v-if="hoveredNode.metadata?.thesis" class="tooltip-field">
        <span class="field-label">Thesis:</span> {{ hoveredNode.metadata.thesis }}
      </div>
      <div v-if="hoveredNode.metadata?.counter" class="tooltip-field">
        <span class="field-label">Counter:</span> {{ hoveredNode.metadata.counter }}
      </div>
      <div v-if="hoveredNode.metadata?.mission" class="tooltip-field">
        <span class="field-label">Mission:</span> {{ hoveredNode.metadata.mission }}
      </div>
      <div class="tooltip-stats">
        <span>Energy: {{ hoveredNode.state.energy.toFixed(2) }}</span>
        <span>Influence: {{ hoveredNode.state.influence.toFixed(2) }}</span>
        <span>Resources: {{ hoveredNode.state.resources.toFixed(2) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  snapshot: { type: Object, default: null },
})

const containerRef = ref(null)
const canvasRef = ref(null)
const hoveredNode = ref(null)
const tooltipStyle = ref({})

// --- Color and size encoding ---
const NODE_COLORS = {
  agent: '#4A90D9',
  institution: '#E5A844',
  idea: '#50B86C',
  resource: '#E8814D',
  environment: '#9B6EC6',
}
const EDGE_COLORS = {
  influence: '#666',
  information: '#4A90D9',
  resource_flow: '#E8814D',
  membership: '#E5A844',
  conflict: '#D94A4A',
  cooperation: '#50B86C',
}

// --- D3 simulation state ---
let simulation = null
let nodes = []
let links = []
let transform = d3.zoomIdentity
let width = 0
let height = 0
let animFrameId = null
let dragNode = null
let isDragging = false
let particles = []
let particleFrame = null

function nodeRadius(n) {
  return Math.max(5, Math.min(25, 4 + Math.sqrt(n.state.energy) * 3))
}

function edgeWidth(e) {
  return Math.max(0.5, Math.min(5, e.weight * 1.5))
}

// --- Initialize simulation ---
function initSimulation() {
  if (!props.snapshot) return
  const snap = props.snapshot

  // Build node/link arrays with D3-compatible fields
  // Scale initial spread with node count so large graphs don't start clumped
  const nCount = snap.nodes.length
  const spread = Math.max(300, Math.sqrt(nCount) * 30)
  nodes = snap.nodes.map(n => ({
    id: n.node_id,
    ...n,
    x: n._x || width / 2 + (Math.random() - 0.5) * spread,
    y: n._y || height / 2 + (Math.random() - 0.5) * spread,
  }))

  const nodeIndex = new Map(nodes.map(n => [n.id, n]))
  links = snap.edges
    .filter(e => nodeIndex.has(e.source_id) && nodeIndex.has(e.target_id))
    .map(e => ({
      source: e.source_id,
      target: e.target_id,
      ...e,
    }))

  if (simulation) simulation.stop()

  // Scale repulsion with node count for better spread
  const baseCharge = nCount > 100 ? -250 : nCount > 50 ? -180 : -120
  const baseLinkDist = nCount > 100 ? 120 : 80

  // Build institution centroid map for clustering force
  const instMembers = new Map()
  for (const n of nodes) {
    if (n.institution_id) {
      if (!instMembers.has(n.institution_id)) instMembers.set(n.institution_id, [])
      instMembers.get(n.institution_id).push(n)
    }
  }

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id)
      .distance(d => baseLinkDist * (1.4 - Math.min(1.0, d.weight) * 0.7))
      .strength(d => {
        const t = d.edge_type
        if (t === 'membership') return 0.6
        if (t === 'cooperation') return 0.25
        if (t === 'influence') return 0.15
        return 0.1
      }))
    .force('charge', d3.forceManyBody()
      .strength(d => baseCharge * (0.4 + Math.min(1.5, Math.sqrt(d.state.energy) * 0.3)))
      .distanceMax(600))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.03))
    .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 1))
    .force('cluster', () => {
      // Pull institutional members toward their group centroid
      for (const [, members] of instMembers) {
        if (members.length < 2) continue
        let cx = 0, cy = 0
        for (const m of members) { cx += m.x; cy += m.y }
        cx /= members.length; cy /= members.length
        for (const m of members) {
          m.vx += (cx - m.x) * 0.008
          m.vy += (cy - m.y) * 0.008
        }
      }
    })
    .alphaDecay(0.012)
    .on('tick', draw)

  startParticleAnimation()
}

// --- Particle animation ---
function spawnParticles() {
  // Spawn new particles along high-weight edges
  for (const link of links) {
    const src = typeof link.source === 'object' ? link.source : null
    const tgt = typeof link.target === 'object' ? link.target : null
    if (!src || !tgt) continue
    // Spawn probability proportional to weight and transfer rate
    const rate = (link.weight || 0.5) * (link.transfer_rate || 0.1)
    if (Math.random() < rate * 0.15) {
      particles.push({
        source: src,
        target: tgt,
        progress: 0,
        speed: 0.01 + Math.random() * 0.02,
        color: EDGE_COLORS[link.edge_type] || '#999',
      })
    }
  }
  // Remove completed particles
  particles = particles.filter(p => p.progress < 1)
}

function updateParticles() {
  for (const p of particles) {
    p.progress += p.speed
  }
}

function drawParticles(ctx) {
  for (const p of particles) {
    const x = p.source.x + (p.target.x - p.source.x) * p.progress
    const y = p.source.y + (p.target.y - p.source.y) * p.progress
    ctx.beginPath()
    ctx.arc(x, y, 2, 0, 2 * Math.PI)
    ctx.fillStyle = p.color
    ctx.globalAlpha = 0.8 * (1 - p.progress * 0.5)
    ctx.fill()
    ctx.globalAlpha = 1
  }
}

function startParticleAnimation() {
  if (particleFrame) cancelAnimationFrame(particleFrame)
  function animate() {
    spawnParticles()
    updateParticles()
    draw()
    particleFrame = requestAnimationFrame(animate)
  }
  particleFrame = requestAnimationFrame(animate)
}

// --- Update node states without resetting positions ---
function updateNodeStates() {
  if (!props.snapshot || !nodes.length) {
    initSimulation()
    return
  }
  const snap = props.snapshot
  const snapMap = new Map(snap.nodes.map(n => [n.node_id, n]))

  for (const node of nodes) {
    const fresh = snapMap.get(node.id)
    if (fresh) {
      node.state = fresh.state
      node.metadata = fresh.metadata
    }
  }
  draw()
}

// --- Canvas rendering ---
function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.save()
  ctx.clearRect(0, 0, width, height)
  ctx.translate(transform.x, transform.y)
  ctx.scale(transform.k, transform.k)

  // Draw edges
  for (const link of links) {
    const src = typeof link.source === 'object' ? link.source : nodes.find(n => n.id === link.source)
    const tgt = typeof link.target === 'object' ? link.target : nodes.find(n => n.id === link.target)
    if (!src || !tgt) continue

    ctx.beginPath()
    ctx.moveTo(src.x, src.y)
    ctx.lineTo(tgt.x, tgt.y)
    ctx.strokeStyle = EDGE_COLORS[link.edge_type] || '#999'
    ctx.globalAlpha = 0.4 + Math.min(0.5, link.weight * 0.2)
    ctx.lineWidth = edgeWidth(link)
    ctx.stroke()
    ctx.globalAlpha = 1

    // Arrowhead
    const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x)
    const r = nodeRadius(tgt)
    const ax = tgt.x - Math.cos(angle) * (r + 3)
    const ay = tgt.y - Math.sin(angle) * (r + 3)
    ctx.beginPath()
    ctx.moveTo(ax, ay)
    ctx.lineTo(ax - 6 * Math.cos(angle - 0.4), ay - 6 * Math.sin(angle - 0.4))
    ctx.lineTo(ax - 6 * Math.cos(angle + 0.4), ay - 6 * Math.sin(angle + 0.4))
    ctx.closePath()
    ctx.fillStyle = EDGE_COLORS[link.edge_type] || '#999'
    ctx.fill()
  }

  // Draw particles along edges
  drawParticles(ctx)

  // Draw nodes
  for (const node of nodes) {
    const r = nodeRadius(node)
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = NODE_COLORS[node.node_type] || '#999'
    ctx.fill()

    // Institution border
    if (node.institution_id) {
      ctx.strokeStyle = '#333'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }

    // Label
    if (transform.k > 0.6) {
      ctx.fillStyle = '#c9d1d9'
      ctx.font = `${Math.max(9, 11 / transform.k)}px sans-serif`
      ctx.textAlign = 'center'
      ctx.fillText(node.label, node.x, node.y + r + 12)
    }
  }

  ctx.restore()
}

// --- Interaction handlers ---
function screenToGraph(sx, sy) {
  return [(sx - transform.x) / transform.k, (sy - transform.y) / transform.k]
}

function findNodeAt(sx, sy) {
  const [gx, gy] = screenToGraph(sx, sy)
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i]
    const r = nodeRadius(n)
    if ((n.x - gx) ** 2 + (n.y - gy) ** 2 < (r + 4) ** 2) return n
  }
  return null
}

function onWheel(e) {
  const factor = e.deltaY > 0 ? 0.9 : 1.1
  const rect = canvasRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  transform = transform.translate(mx, my).scale(factor).translate(-mx, -my)
  draw()
}

let dragStartX = 0, dragStartY = 0

function onMouseDown(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const node = findNodeAt(mx, my)
  if (node) {
    dragNode = node
    dragNode.fx = dragNode.x
    dragNode.fy = dragNode.y
    if (simulation) simulation.alphaTarget(0.3).restart()
  }
  isDragging = true
  dragStartX = mx
  dragStartY = my
}

function onMouseMove(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top

  if (isDragging && dragNode) {
    const [gx, gy] = screenToGraph(mx, my)
    dragNode.fx = gx
    dragNode.fy = gy
  } else if (isDragging) {
    // Pan
    transform = transform.translate(
      (mx - dragStartX) / transform.k,
      (my - dragStartY) / transform.k
    )
    dragStartX = mx
    dragStartY = my
    draw()
  } else {
    // Hover
    const node = findNodeAt(mx, my)
    if (node) {
      hoveredNode.value = node
      tooltipStyle.value = {
        left: `${mx + 12}px`,
        top: `${my - 10}px`,
      }
    } else {
      hoveredNode.value = null
    }
  }
}

function onMouseUp() {
  if (dragNode) {
    dragNode.fx = null
    dragNode.fy = null
    dragNode = null
    if (simulation) simulation.alphaTarget(0)
  }
  isDragging = false
}

function onDblClick(e) {
  // Zoom to fit
  if (!nodes.length) return
  const xs = nodes.map(n => n.x)
  const ys = nodes.map(n => n.y)
  const xMin = Math.min(...xs) - 40
  const xMax = Math.max(...xs) + 40
  const yMin = Math.min(...ys) - 40
  const yMax = Math.max(...ys) + 40
  const scale = Math.min(width / (xMax - xMin), height / (yMax - yMin)) * 0.9
  const cx = (xMin + xMax) / 2
  const cy = (yMin + yMax) / 2
  transform = d3.zoomIdentity.translate(width / 2 - cx * scale, height / 2 - cy * scale).scale(scale)
  draw()
}

// --- Resize ---
function resize() {
  const el = containerRef.value
  if (!el) return
  width = el.clientWidth
  height = el.clientHeight
  const canvas = canvasRef.value
  if (canvas) {
    canvas.width = width * devicePixelRatio
    canvas.height = height * devicePixelRatio
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
    const ctx = canvas.getContext('2d')
    ctx.scale(devicePixelRatio, devicePixelRatio)
  }
  if (simulation) simulation.force('center', d3.forceCenter(width / 2, height / 2))
  draw()
}

// --- Watch snapshot changes ---
watch(() => props.snapshot, (newVal, oldVal) => {
  if (!newVal) return
  if (!oldVal || newVal.timestep === 0) {
    initSimulation()
  } else {
    updateNodeStates()
  }
})

let resizeObserver = null

onMounted(() => {
  resize()
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(containerRef.value)
  if (props.snapshot) initSimulation()
})

onUnmounted(() => {
  if (simulation) simulation.stop()
  if (animFrameId) cancelAnimationFrame(animFrameId)
  if (particleFrame) cancelAnimationFrame(particleFrame)
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<style scoped>
.dynamics-graph-panel {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: #0d1117;
  border-radius: 8px;
  overflow: hidden;
}
canvas {
  display: block;
  cursor: grab;
}
canvas:active {
  cursor: grabbing;
}
.tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(13, 17, 23, 0.95);
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 8px 12px;
  color: #e6edf3;
  font-size: 12px;
  z-index: 10;
  max-width: 300px;
}
.tooltip-desc {
  font-size: 11px;
  color: #b1bac4;
  margin-bottom: 4px;
  line-height: 1.4;
}
.tooltip-field {
  font-size: 11px;
  color: #8b949e;
  line-height: 1.4;
  margin-bottom: 1px;
}
.tooltip-field .field-label {
  color: #c9d1d9;
  font-weight: 600;
}
.tooltip-label {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 2px;
}
.tooltip-type {
  color: #8b949e;
  font-size: 11px;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.tooltip-stats {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  color: #8b949e;
}
</style>
