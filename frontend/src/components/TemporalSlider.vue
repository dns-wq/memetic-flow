<template>
  <div class="temporal-slider">
    <div class="controls">
      <button class="ctrl-btn" @click="togglePlay" :title="playing ? 'Pause' : 'Play'">
        {{ playing ? '||' : '>' }}
      </button>
      <input type="range" class="slider" :min="0" :max="maxTimestep"
             :value="modelValue" @input="onSliderInput" />
      <span class="timestep-label">t={{ modelValue }} / {{ maxTimestep }}</span>
      <select class="speed-select" v-model="speed">
        <option :value="0.5">0.5x</option>
        <option :value="1">1x</option>
        <option :value="2">2x</option>
        <option :value="5">5x</option>
      </select>
    </div>
    <div v-if="events.length" class="event-markers">
      <div v-for="(evt, i) in events" :key="i" class="event-dot"
           :style="{ left: `${(evt.timestep / Math.max(1, maxTimestep)) * 100}%` }"
           :title="`${evt.event_type}: ${evt.metric_name} (t=${evt.timestep})`"
           :class="evt.event_type" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  maxTimestep: { type: Number, default: 0 },
  events: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const playing = ref(false)
const speed = ref(1)
let intervalId = null

function togglePlay() {
  playing.value = !playing.value
  if (playing.value) startPlayback()
  else stopPlayback()
}

function startPlayback() {
  stopPlayback()
  intervalId = setInterval(() => {
    if (props.modelValue >= props.maxTimestep) {
      playing.value = false
      stopPlayback()
      return
    }
    emit('update:modelValue', props.modelValue + 1)
  }, 200 / speed.value)
}

function stopPlayback() {
  if (intervalId) clearInterval(intervalId)
  intervalId = null
}

function onSliderInput(e) {
  emit('update:modelValue', parseInt(e.target.value))
}

watch(speed, () => { if (playing.value) startPlayback() })

onUnmounted(stopPlayback)
</script>

<style scoped>
.temporal-slider {
  background: #161b22;
  border-radius: 8px;
  padding: 10px 14px;
  position: relative;
}
.controls {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ctrl-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #30363d;
  border-radius: 4px;
  background: #21262d;
  color: #e6edf3;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ctrl-btn:hover { background: #30363d; }
.slider {
  flex: 1;
  accent-color: #58a6ff;
}
.timestep-label {
  font-size: 12px;
  color: #8b949e;
  min-width: 80px;
  text-align: right;
}
.speed-select {
  font-size: 11px;
  background: #21262d;
  color: #e6edf3;
  border: 1px solid #30363d;
  border-radius: 4px;
  padding: 2px 4px;
}
.event-markers {
  position: relative;
  height: 8px;
  margin-top: 4px;
  margin-left: 38px;
  margin-right: 140px;
}
.event-dot {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  transform: translateX(-3px);
}
.event-dot.spike { background: #f85149; }
.event-dot.drop { background: #58a6ff; }
</style>
