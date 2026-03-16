/**
 * Static mode definitions for the demo site.
 * These match the backend mode registry but are embedded here
 * so the demo site works without any backend.
 */
export const MODE_DEFINITIONS = [
  {
    name: 'custom',
    description: 'Manual template selection — full control over dynamics configuration.',
    icon: 'settings',
  },
  {
    name: 'synthetic_civilization',
    description: 'Institutional emergence, norm formation, and technology diffusion. Watch civilizations form from scratch.',
    icon: 'castle',
  },
  {
    name: 'ecosystem',
    description: 'Cognitive ecology and attention economy. Species-like strategies compete and evolve.',
    icon: 'brain',
  },
  {
    name: 'memetic_physics',
    description: 'Ideas as particles in conceptual fields. Measure force, mass, and entropy of memes.',
    icon: 'atom',
  },
  {
    name: 'market_dynamics',
    description: 'Price formation, competitive dynamics, and supply chain flows. Model economic systems.',
    icon: 'trending',
  },
  {
    name: 'public_discourse',
    description: 'Electoral dynamics, coalition formation, and deliberation. Simulate democratic processes.',
    icon: 'megaphone',
  },
  {
    name: 'knowledge_ecosystems',
    description: 'Scientific discovery, peer review, and paradigm shifts. Model the production of knowledge.',
    icon: 'microscope',
  },
  {
    name: 'ecological_systems',
    description: 'Population ecology, habitat dynamics, and ecosystem services. Model environmental systems.',
    icon: 'leaf',
  },
]

export const MODE_COLORS = {
  custom: '#8b949e',
  synthetic_civilization: '#d2a8ff',
  ecosystem: '#3fb950',
  memetic_physics: '#f0883e',
  market_dynamics: '#58a6ff',
  public_discourse: '#f85149',
  knowledge_ecosystems: '#a371f7',
  ecological_systems: '#56d364',
}
