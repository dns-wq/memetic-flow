/**
 * API client for the dynamics simulation engine.
 */
import api from './index'

// --- Graph initialization ---

export function initializeDynamics(graphData, ontology = null) {
  return api.post('/api/dynamics/initialize', { graph_data: graphData, ontology })
}

// --- Graph state ---

export function getGraph(simId) {
  return api.get(`/api/dynamics/graph/${simId}`)
}

export function getSnapshot(simId, timestep) {
  return api.get(`/api/dynamics/snapshot/${simId}/${timestep}`)
}

// --- Templates ---

export function listTemplates() {
  return api.get('/api/dynamics/templates')
}

export function getTemplateParameters(templateName) {
  return api.get(`/api/dynamics/parameters/${templateName}`)
}

// --- Configuration ---

export function configureDynamics(simId, templates, params = {}, seed = 42) {
  return api.post('/api/dynamics/configure', {
    sim_id: simId,
    templates,
    params,
    seed,
  })
}

// --- Simulation control ---

export function startDynamics(simId, steps = 100) {
  return api.post('/api/dynamics/start', { sim_id: simId, steps })
}

export function stopDynamics(simId) {
  return api.post('/api/dynamics/stop', { sim_id: simId })
}

export function getDynamicsStatus(simId) {
  return api.get(`/api/dynamics/status/${simId}`)
}

// --- Metrics & events ---

export function getMetrics(simId, metric = null) {
  const params = metric ? { metric } : {}
  return api.get(`/api/dynamics/metrics/${simId}`, { params })
}

export function getEvents(simId) {
  return api.get(`/api/dynamics/events/${simId}`)
}

// --- Manual intervention ---

export function injectEvent(simId, template, params) {
  return api.post('/api/dynamics/inject-event', {
    sim_id: simId,
    template,
    params,
  })
}

// --- Export ---

export function exportJSON(simId) {
  return api.get(`/api/dynamics/export/${simId}/json`, { responseType: 'blob' })
}

export function exportCSV(simId) {
  return api.get(`/api/dynamics/export/${simId}/csv`, { responseType: 'blob' })
}

// --- Scenario comparison ---

export function compareScenarios(simId, paramsA, paramsB, steps = 100) {
  return api.post('/api/dynamics/compare', {
    sim_id: simId,
    params_a: paramsA,
    params_b: paramsB,
    steps,
  })
}

// --- Modes ---

export function listModes() {
  return api.get('/api/dynamics/modes')
}

export function applyMode(simId, modeName) {
  return api.post(`/api/dynamics/modes/${modeName}/apply`, { sim_id: simId })
}

// --- Demos ---

export function listDemos() {
  return api.get('/api/dynamics/demos')
}

export function loadDemo(demoName) {
  return api.post(`/api/dynamics/demo/${demoName}/load`)
}
