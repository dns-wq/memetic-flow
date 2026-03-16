/**
 * Static data loader for the demo site.
 * Replaces the axios API layer — loads pre-exported JSON via fetch().
 */

const BASE = import.meta.env.BASE_URL + 'data'

const cache = new Map()

async function fetchJSON(path) {
  if (cache.has(path)) return cache.get(path)
  const resp = await fetch(`${BASE}/${path}`)
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status}`)
  const data = await resp.json()
  cache.set(path, data)
  return data
}

async function fetchText(path) {
  if (cache.has(path)) return cache.get(path)
  const resp = await fetch(`${BASE}/${path}`)
  if (!resp.ok) return null // Document may not exist for all scenarios
  const text = await resp.text()
  cache.set(path, text)
  return text
}

/** Load the scenarios manifest */
export async function loadManifest() {
  return fetchJSON('scenarios.json')
}

/** Load all mode definitions */
export async function loadModes() {
  return fetchJSON('modes.json')
}

/** Load metadata for a scenario */
export async function loadMetadata(scenario) {
  return fetchJSON(`${scenario}/metadata.json`)
}

/** Load the final graph state for a scenario */
export async function loadGraph(scenario) {
  return fetchJSON(`${scenario}/graph.json`)
}

/** Load metrics time series for a scenario */
export async function loadMetrics(scenario) {
  return fetchJSON(`${scenario}/metrics.json`)
}

/** Load events for a scenario */
export async function loadEvents(scenario) {
  return fetchJSON(`${scenario}/events.json`)
}

/** Load the source document markdown for a scenario (may return null) */
export async function loadDocument(scenario) {
  return fetchText(`${scenario}/document.md`)
}

/** Load all sampled snapshots for a scenario (cached after first load) */
export async function loadSnapshots(scenario) {
  return fetchJSON(`${scenario}/snapshots.json`)
}

/**
 * Get the snapshot nearest to the requested timestep.
 * Snapshots are sampled every 25 steps, so we find the closest one.
 */
export async function getSnapshot(scenario, timestep) {
  const snapshots = await loadSnapshots(scenario)
  if (!snapshots.length) return null

  // Find nearest snapshot
  let best = snapshots[0]
  let bestDist = Math.abs(best.timestep - timestep)
  for (const snap of snapshots) {
    const dist = Math.abs(snap.timestep - timestep)
    if (dist < bestDist) {
      best = snap
      bestDist = dist
    }
  }
  return best.data
}

/**
 * Load all data for a scenario in parallel.
 * Returns { metadata, graph, metrics, events }.
 */
export async function loadScenarioData(scenario) {
  const [metadata, graph, metrics, events] = await Promise.all([
    loadMetadata(scenario),
    loadGraph(scenario),
    loadMetrics(scenario),
    loadEvents(scenario),
  ])
  return { metadata, graph, metrics, events }
}
