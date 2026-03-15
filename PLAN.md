# Memetic Flow — Implementation Plan

## Context

**Problem:** MiroFish simulates agent societies using LLM agents chatting on simulated social platforms, but lacks structured dynamical modeling. Agents interact via free-form text, producing narratives rather than reproducible, analyzable system dynamics. There is no feedback loop structure, no explicit evolution rules, and no macro-level measurement.

**Goal:** Fork MiroFish and layer a **unified dynamical simulation engine** on top of its OASIS agent framework. The engine introduces typed graphs with directed/circular edges, template-based evolution equations, institutional grouping, and a new D3.js force-graph visualization. This transforms MiroFish from a conversational agent demo into a complex systems laboratory.

**Outcome:** A working prototype ("Memetic Flow") where users upload documents, the system extracts a typed entity graph, runs both OASIS agent interactions AND explicit dynamical simulations, and visualizes emergent system dynamics through interactive force graphs.

---

## Architecture Overview

```
Document Upload
       │
       ▼
┌─────────────────────┐
│ Interpretation Layer │  Claude API: extract entities, relations, causal claims
│ (modified MiroFish)  │  → typed graph primitives
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Typed Graph Model   │  Nodes (Agent/Institution/Idea/Resource) + directed weighted edges
│  (new: dynamics/)    │  State variables, circularity support, institutional grouping
└──────────┬──────────┘
           ▼
┌─────────────────────────────────────────┐
│         Simulation Layer                 │
│  ┌───────────┐    ┌──────────────────┐  │
│  │   OASIS    │◄──►│ Dynamical Engine │  │
│  │ (existing) │    │ (new: engine/)   │  │
│  └───────────┘    └──────────────────┘  │
│   Agent chat &     Template equations,   │
│   social actions   graph state updates   │
└──────────┬──────────────────┬───────────┘
           ▼                  ▼
┌─────────────────────┐  ┌──────────────┐
│ Measurement Layer   │  │ Report Agent │
│ (new: metrics/)     │  │ (existing)   │
│ Entropy, clustering,│  └──────────────┘
│ polarization, Gini  │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Visualization      │
│ D3.js Force Graph    │  Canvas rendering, temporal replay,
│ (new Vue component)  │  animated flows, metric dashboard
└─────────────────────┘
```

---

## Phase 1: Fork & Foundation

**Goal:** Fork MiroFish, switch LLM provider to Claude, establish project structure.

### 1.1 Fork and rebrand
- Fork `github.com/666ghj/MiroFish` → `memetic-flow`
- Update branding: project name, README, logos
- Retain AGPL-3.0 license with original copyright notice
- Add new copyright for Memetic Flow additions

### 1.2 Replace LLM provider
- **Modify:** `backend/app/utils/llm_client.py`
  - Replace `openai` SDK with `anthropic` SDK
  - Maintain the same interface (`call_llm(messages, model, temperature)`) so all services work without changes
  - Default model: `claude-sonnet-4-6` (cost-effective for extraction tasks)
  - Environment variable: `ANTHROPIC_API_KEY` replaces `LLM_API_KEY`

### 1.3 Create new directory structure
```
backend/app/
├── dynamics/              # NEW: typed graph data model
│   ├── __init__.py
│   ├── models.py          # Node, Edge, Institution, GraphSnapshot
│   ├── graph.py           # DynamicsGraph class (CRUD + query)
│   └── persistence.py     # SQLite storage for graph snapshots
├── engine/                # NEW: dynamical simulation engine
│   ├── __init__.py
│   ├── templates/         # Equation template families
│   │   ├── __init__.py
│   │   ├── base.py        # Abstract DynamicsTemplate interface
│   │   ├── diffusion.py   # Idea/information spreading
│   │   ├── opinion.py     # Bounded confidence / voter models
│   │   ├── evolutionary.py # Replicator dynamics
│   │   ├── resource.py    # Lotka-Volterra resource competition
│   │   └── feedback.py    # System dynamics (stocks & flows)
│   ├── runner.py          # SimulationEngine orchestrator
│   ├── oasis_bridge.py    # OASIS action → graph update mapping
│   └── calibration.py     # Empirical priors + parameter ranges
├── metrics/               # NEW: measurement & observation
│   ├── __init__.py
│   ├── collectors.py      # Metric computation functions
│   └── detectors.py       # Phase transition detection
├── api/
│   ├── dynamics.py        # NEW: API endpoints for dynamics engine
│   └── ... (existing)
```

```
frontend/src/
├── components/
│   ├── DynamicsGraphPanel.vue    # NEW: D3 force graph visualization
│   ├── MetricsDashboard.vue      # NEW: time-series metric charts
│   ├── TemplateSelector.vue      # NEW: dynamics template picker
│   ├── TemporalSlider.vue        # NEW: timeline scrubber
│   └── ... (existing)
├── views/
│   ├── DynamicsView.vue          # NEW: main dynamics simulation view
│   └── ... (existing)
├── api/
│   ├── dynamics.js               # NEW: dynamics API client
│   └── ... (existing)
```

### 1.4 Verification
- Run existing MiroFish with Claude API — confirm ontology generation, graph building, and simulation work
- Run `pytest` on existing tests

---

## Phase 2: Typed Graph Data Model

**Goal:** Define the core data structures that all other components depend on.

### 2.1 Node model — `backend/app/dynamics/models.py`

```python
class NodeType(str, Enum):
    AGENT = "agent"
    INSTITUTION = "institution"
    IDEA = "idea"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"

class NodeState(BaseModel):
    """Extensible state vector for a node."""
    resources: float = 1.0
    stability: float = 1.0
    influence: float = 0.5
    ideological_position: list[float] = []   # N-dimensional opinion vector
    mutation_rate: float = 0.01
    energy: float = 1.0
    custom: dict[str, float] = {}            # User-defined state vars

class GraphNode(BaseModel):
    node_id: str
    node_type: NodeType
    label: str
    state: NodeState
    institution_id: str | None = None        # Group membership
    source_entity_id: str | None = None      # Link to Zep/OASIS entity
    metadata: dict = {}
```

### 2.2 Edge model

```python
class EdgeType(str, Enum):
    INFLUENCE = "influence"
    INFORMATION = "information"
    RESOURCE_FLOW = "resource_flow"
    MEMBERSHIP = "membership"
    CONFLICT = "conflict"
    COOPERATION = "cooperation"

class GraphEdge(BaseModel):
    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    transfer_rate: float = 0.1
    decay_rate: float = 0.01
    metadata: dict = {}
```

### 2.3 Graph snapshot and timeline

```python
class GraphSnapshot(BaseModel):
    """Complete graph state at a point in time."""
    timestep: int
    nodes: dict[str, GraphNode]
    edges: dict[str, GraphEdge]
    institutions: dict[str, list[str]]       # institution_id → [node_ids]
    metrics: dict[str, float] = {}           # Computed macro metrics
    timestamp: datetime

class DynamicsGraph:
    """Mutable graph with history tracking."""
    def __init__(self, seed: GraphSnapshot): ...
    def add_node(self, node: GraphNode): ...
    def add_edge(self, edge: GraphEdge): ...
    def update_node_state(self, node_id: str, updates: dict): ...
    def get_neighbors(self, node_id: str, direction: str = "out") -> list[str]: ...
    def get_feedback_loops(self, max_length: int = 5) -> list[list[str]]: ...
    def snapshot(self) -> GraphSnapshot: ...
    def history(self) -> list[GraphSnapshot]: ...
```

### 2.4 Persistence — `backend/app/dynamics/persistence.py`
- SQLite database (`dynamics.db`) alongside OASIS trace DB
- Tables: `nodes`, `edges`, `snapshots`, `metrics_timeseries`
- Save/load full graph snapshots per timestep
- Query metrics time series for visualization

### 2.5 Verification
- Unit tests: create graph, add nodes/edges, verify circularity detection
- Test snapshot save/load round-trip

---

## Phase 3: Template Dynamical Engine

**Goal:** Implement the simulation core — explicit mathematical update rules, not LLM improvisation.

### 3.1 Template interface — `backend/app/engine/templates/base.py`

```python
class DynamicsTemplate(ABC):
    """Base class for all dynamical equation templates."""
    name: str
    description: str
    required_node_types: list[NodeType]
    required_edge_types: list[EdgeType]
    parameters: dict[str, ParameterSpec]     # name → (default, min, max, description)

    @abstractmethod
    def update(self, graph: DynamicsGraph, params: dict, rng: np.random.Generator) -> None:
        """Apply one timestep of dynamics. Mutates graph state in place."""
        ...

    def get_empirical_priors(self) -> dict[str, float]:
        """Return default parameter values from literature."""
        ...
```

### 3.2 Template implementations (5 families)

**Diffusion** (`diffusion.py`): Information/idea spreading via edges.
- Update rule: `node.state.energy += sum(edge.transfer_rate * neighbor.state.energy * edge.weight) - node.state.energy * decay`
- Parameters: `transfer_rate`, `decay_rate`, `threshold` (minimum energy to transmit)
- Priors from network science (cascade probability ~0.01-0.05 per edge per step)

**Opinion dynamics** (`opinion.py`): Bounded-confidence belief updating.
- Update rule: agents adjust ideological_position toward neighbors within a tolerance threshold
- Parameters: `tolerance`, `convergence_rate`, `noise_std`
- Priors from Hegselmann-Krause model (tolerance ~0.2-0.4)

**Evolutionary competition** (`evolutionary.py`): Replicator dynamics for competing strategies/memes.
- Update rule: idea fitness ∝ adoption count; ideas replicate proportional to fitness, mutate with probability
- Parameters: `selection_strength`, `mutation_rate`, `carrying_capacity`
- Priors from evolutionary game theory

**Resource flow** (`resource.py`): Competition and predation dynamics.
- Update rule: Lotka-Volterra-inspired resource equations with network-mediated flows
- Parameters: `growth_rate`, `competition_coefficient`, `flow_rate`
- Priors from ecological modeling

**Feedback systems** (`feedback.py`): Stocks-and-flows with circular causation.
- Update rule: node.state += inflows - outflows; edges define flow rates
- Parameters: `flow_coefficients`, `saturation_limits`, `delay_steps`
- Priors from system dynamics literature

### 3.3 Engine runner — `backend/app/engine/runner.py`

```python
class SimulationEngine:
    def __init__(self, graph: DynamicsGraph, templates: list[DynamicsTemplate],
                 params: dict, seed: int = 42): ...

    def step(self) -> GraphSnapshot:
        """Run one timestep: apply all templates sequentially, compute metrics."""
        for template in self.templates:
            template.update(self.graph, self.params[template.name], self.rng)
        snapshot = self.graph.snapshot()
        snapshot.metrics = self.metrics_collector.compute(self.graph)
        self.graph.save_snapshot(snapshot)
        return snapshot

    def run(self, steps: int, callback=None) -> list[GraphSnapshot]: ...
    def set_params(self, template_name: str, params: dict): ...
```

### 3.4 OASIS bridge — `backend/app/engine/oasis_bridge.py`

Maps OASIS agent actions to typed graph updates:

| OASIS Action | Graph Update |
|---|---|
| `CREATE_POST` | Create Idea node, add Information edges to followers |
| `LIKE_POST` / `DISLIKE_POST` | Increase/decrease edge weight on Information edge |
| `FOLLOW` / `UNFOLLOW` | Create/remove Influence edge |
| `CREATE_COMMENT` | Add Information edge between commenter and post author |
| `REPOST` | Amplify idea node energy, create new edges |

Integration hook: After each OASIS simulation round, `oasis_bridge.ingest_actions(action_log)` reads the JSONL action file and updates the dynamics graph. Optionally, graph state feeds back into OASIS agent behavior via modified influence weights in the RecSys.

### 3.5 Verification
- Unit tests per template: known input → expected output for simple 3-node graphs
- Integration test: run engine for 100 steps, verify convergence/divergence matches expected dynamics
- Reproducibility test: same seed → same trajectory

---

## Phase 4: Measurement & Observation Layer

**Goal:** Compute macro-level metrics that turn raw simulation into interpretable analysis.

### 4.1 Metric collectors — `backend/app/metrics/collectors.py`

```python
class MetricsCollector:
    def compute(self, graph: DynamicsGraph) -> dict[str, float]:
        return {
            "idea_entropy": self._idea_entropy(graph),
            "polarization_index": self._polarization(graph),
            "clustering_coefficient": self._clustering(graph),
            "institutional_cohesion": self._cohesion(graph),
            "resource_gini": self._gini(graph),
            "cascade_count": self._cascades(graph),
            "feedback_loop_strength": self._loop_strength(graph),
            "total_energy": self._total_energy(graph),
        }
```

### 4.2 Phase transition detection — `backend/app/metrics/detectors.py`
- Monitor metric time series for abrupt changes (derivative exceeds threshold)
- Detect: polarization spikes, institutional collapse, cascade events
- Output events for visualization layer to highlight

### 4.3 Verification
- Unit tests with synthetic graphs of known metric values
- Verify Gini = 0 for equal distribution, = 1 for maximal inequality, etc.

---

## Phase 5: Enhanced Document Interpretation

**Goal:** Upgrade entity extraction to produce typed graph primitives suitable for the dynamical engine.

### 5.1 Modify ontology generator — `backend/app/services/ontology_generator.py`
- Extend entity type classification to map to `NodeType` enum (agent, institution, idea, resource, environment)
- Extract **causal claims** from documents (e.g., "Policy X causes outcome Y" → directed Influence edge)
- Extract **resource relationships** (e.g., "Company A competes with B for market share" → ResourceFlow edges)
- Output includes suggested dynamical templates based on extracted relationship patterns

### 5.2 Graph initialization — `backend/app/services/dynamics_initializer.py` (new)
- Takes ontology + Zep knowledge graph entities
- Creates a `DynamicsGraph` with properly typed nodes and edges
- Assigns initial state values from empirical priors
- Detects likely template matches from relationship patterns:
  - Many information edges → suggest Diffusion template
  - Opinion/stance attributes → suggest Opinion Dynamics
  - Resource mentions → suggest Resource Flow
  - Circular causal chains → suggest Feedback Systems

### 5.3 Verification
- Upload a policy paper → verify typed graph output has correct node/edge types
- Verify template suggestion makes sense for the document domain

---

## Phase 6: D3.js Force Graph Visualization

**Goal:** Replace the chat-log view with an interactive dynamics visualization.

### 6.1 Core graph component — `frontend/src/components/DynamicsGraphPanel.vue`

**Architecture:** Vue 3 Composition API + Canvas rendering.

```
DynamicsGraphPanel.vue
├── Canvas element (ref)
├── D3 force simulation (in web worker if >500 nodes)
├── Node rendering: circles colored/sized by type and state
├── Edge rendering: lines with arrowheads, thickness = weight
├── Animated particles along edges showing flow direction
├── Click/hover interactions for node/edge inspection
└── Zoom/pan with d3-zoom
```

**Visual encoding:**
| Element | Visual Property | Data Binding |
|---|---|---|
| Node color | Fill | `NodeType` (agent=blue, institution=gold, idea=green, resource=orange) |
| Node size | Radius | `node.state.influence` or `node.state.energy` |
| Node border | Stroke | Institution membership (same color = same institution) |
| Edge thickness | Stroke-width | `edge.weight` |
| Edge opacity | Opacity | `edge.transfer_rate` |
| Edge arrows | SVG markers | Direction |
| Flow particles | Animated dots | `edge.weight * transfer_rate` (speed) |

### 6.2 Temporal slider — `frontend/src/components/TemporalSlider.vue`
- Scrubber for replaying simulation history
- Play/pause/speed controls
- Shows current timestep and key events (phase transitions)

### 6.3 Metrics dashboard — `frontend/src/components/MetricsDashboard.vue`
- Small multiple line charts for each metric over time
- Vertical line synchronized with temporal slider
- Highlight phase transition events
- Use a lightweight chart library (Chart.js or D3 line charts)

### 6.4 Template selector — `frontend/src/components/TemplateSelector.vue`
- UI for choosing which dynamical templates to apply
- Parameter adjustment sliders with empirical prior defaults
- Description of each template and what behavior it models

### 6.5 Dynamics view — `frontend/src/views/DynamicsView.vue`
- New step in the workflow (Step 3.5: between environment setup and report)
- Layout: graph panel (left 2/3), metrics + controls (right 1/3)
- Integrates all dynamics components

### 6.6 API client — `frontend/src/api/dynamics.js`
- Axios client for `/api/dynamics/` endpoints
- WebSocket or polling for real-time graph updates during simulation

### 6.7 Verification
- Render a test graph with 100 nodes, verify Canvas performance
- Verify temporal slider replays snapshots correctly
- Verify metric charts update in sync

---

## Phase 7: API Endpoints

**Goal:** Expose dynamics engine functionality to the frontend.

### 7.1 New endpoints — `backend/app/api/dynamics.py`

```
POST   /api/dynamics/initialize          # Create dynamics graph from project
GET    /api/dynamics/graph/<sim_id>       # Get current graph state
GET    /api/dynamics/snapshot/<sim_id>/<timestep>  # Get historical snapshot

GET    /api/dynamics/templates            # List available templates
POST   /api/dynamics/configure            # Set templates + parameters for simulation
GET    /api/dynamics/parameters/<template> # Get parameter specs + priors

POST   /api/dynamics/start               # Start dynamics simulation
POST   /api/dynamics/stop                # Stop dynamics simulation
GET    /api/dynamics/status/<sim_id>      # Simulation progress

GET    /api/dynamics/metrics/<sim_id>     # Metric time series
GET    /api/dynamics/events/<sim_id>      # Phase transition events

POST   /api/dynamics/inject-event        # Manually inject an event (parameter shock)
```

### 7.2 Integration with existing simulation API
- Modify `backend/app/api/simulation.py` to optionally trigger dynamics engine alongside OASIS
- Add `dynamics_enabled` flag to simulation creation
- Bridge runs automatically when enabled

### 7.3 Verification
- API tests: create graph, configure templates, run simulation, retrieve metrics
- End-to-end: upload document → build graph → run dynamics → view in frontend

---

## Implementation Order & Dependencies

```
Phase 1 (Fork & Foundation)      ← No dependencies, do first
    │
Phase 2 (Graph Data Model)      ← Depends on Phase 1
    │
    ├── Phase 3 (Engine)         ← Depends on Phase 2
    │       │
    │       └── Phase 4 (Metrics) ← Depends on Phase 2 + 3
    │
    └── Phase 5 (Interpretation)  ← Depends on Phase 2
            │
Phase 6 (Visualization)          ← Depends on Phase 2, 4
    │
Phase 7 (API)                    ← Depends on Phase 3, 4, 6
    │
Integration Testing              ← Depends on all phases
```

Phases 3, 4, and 5 can be parallelized after Phase 2 is complete.

---

## Key Files Summary

| File | Action | Purpose |
|---|---|---|
| `backend/app/utils/llm_client.py` | Modify | Replace OpenAI → Anthropic SDK |
| `backend/app/dynamics/models.py` | New | Core Pydantic data models |
| `backend/app/dynamics/graph.py` | New | DynamicsGraph class |
| `backend/app/dynamics/persistence.py` | New | SQLite storage |
| `backend/app/engine/templates/base.py` | New | Template abstract interface |
| `backend/app/engine/templates/diffusion.py` | New | Diffusion dynamics |
| `backend/app/engine/templates/opinion.py` | New | Opinion dynamics |
| `backend/app/engine/templates/evolutionary.py` | New | Replicator dynamics |
| `backend/app/engine/templates/resource.py` | New | Resource competition |
| `backend/app/engine/templates/feedback.py` | New | System dynamics |
| `backend/app/engine/runner.py` | New | Simulation orchestrator |
| `backend/app/engine/oasis_bridge.py` | New | OASIS ↔ dynamics integration |
| `backend/app/engine/calibration.py` | New | Empirical priors |
| `backend/app/metrics/collectors.py` | New | Metric computation |
| `backend/app/metrics/detectors.py` | New | Phase transition detection |
| `backend/app/services/ontology_generator.py` | Modify | Add typed extraction + causal claims |
| `backend/app/services/dynamics_initializer.py` | New | Document → typed graph |
| `backend/app/api/dynamics.py` | New | REST API endpoints |
| `backend/app/api/simulation.py` | Modify | Add dynamics_enabled flag |
| `frontend/src/components/DynamicsGraphPanel.vue` | New | D3 force graph |
| `frontend/src/components/MetricsDashboard.vue` | New | Metric charts |
| `frontend/src/components/TemplateSelector.vue` | New | Template picker UI |
| `frontend/src/components/TemporalSlider.vue` | New | Timeline scrubber |
| `frontend/src/views/DynamicsView.vue` | New | Main dynamics page |
| `frontend/src/api/dynamics.js` | New | API client |
| `backend/app/config.py` | Modify | Add dynamics config vars |

---

## Post-MVP Roadmap: Simulation Modes & Extended Templates

Phases 1–7 deliver the **unified engine**. The following phases build on that engine to deliver the three flagship simulation modes discussed in the design conversation, plus additional templates and features that expand the system's applicability.

---

## Phase 8: Simulation Modes Framework

**Goal:** Add a "mode" abstraction layer that bundles specific templates, node types, visualization presets, and metrics into curated experiences. Each mode is a configuration profile over the unified engine — not a separate codebase.

### 8.1 Mode definition — `backend/app/modes/base.py`

```python
class SimulationMode(ABC):
    name: str
    description: str
    icon: str                                    # For UI
    required_templates: list[str]                # Template names to activate
    optional_templates: list[str]                # User can toggle
    default_params: dict[str, dict]              # Per-template parameter overrides
    node_type_config: dict[NodeType, dict]       # Which node types are primary, visual config
    edge_type_config: dict[EdgeType, dict]       # Which edge types are primary
    visualization_preset: str                    # D3 layout preset name
    metrics_focus: list[str]                     # Which metrics to surface prominently
    suggested_for: list[str]                     # Document/domain keywords that suggest this mode

    @abstractmethod
    def initialize_graph(self, base_graph: DynamicsGraph) -> DynamicsGraph:
        """Apply mode-specific initialization logic to the extracted graph."""
        ...

    @abstractmethod
    def post_step_hook(self, graph: DynamicsGraph, timestep: int) -> None:
        """Mode-specific logic after each simulation step (e.g., institutional emergence checks)."""
        ...
```

### 8.2 Mode selection UX
- After document interpretation suggests templates, also suggest matching modes
- User can pick a mode (which auto-configures templates + params) or stay in "custom" mode
- `frontend/src/components/ModeSelector.vue` — card-based picker with descriptions and preview images

### 8.3 Mode registry — `backend/app/modes/__init__.py`
- Auto-discovers mode classes from `modes/` directory
- API endpoint: `GET /api/dynamics/modes` returns available modes with metadata

### 8.4 New files
```
backend/app/modes/
├── __init__.py            # Mode registry
├── base.py                # SimulationMode ABC
├── synthetic_civ.py       # Phase 9
├── ecosystem.py           # Phase 10
├── memetic_physics.py     # Phase 11
├── market_dynamics.py     # Phase 12
├── public_discourse.py    # Phase 13
├── knowledge_ecosystems.py # Phase 14
├── ecological_systems.py  # Phase 15
└── custom.py              # Passthrough mode for manual template selection
```

```
frontend/src/components/
├── ModeSelector.vue       # Mode picker UI
```

---

## Phase 9: Synthetic Civilizations Mode

**Goal:** Simulate the emergence of institutions, laws, economies, and political factions from agent interactions. Agents begin as survival-driven actors; over time they invent norms and structures.

### 9.1 Additional templates

**Institutional emergence** — `backend/app/engine/templates/institutional.py`
- Tracks cooperation frequency between agents; when a cluster exceeds a cohesion threshold, an Institution node is automatically created
- Institutions impose behavioral constraints on members (modify member influence weights and action probabilities)
- Institutions can merge, split, or collapse based on internal cohesion metrics
- Parameters: `formation_threshold`, `cohesion_decay`, `constraint_strength`
- Priors from institutional economics (Douglass North)

**Norm formation** — `backend/app/engine/templates/norms.py`
- Agents develop shared behavioral rules through repeated interaction
- Norms are represented as Idea nodes with high stability and low mutation rate
- Norm adoption follows conformity dynamics: agents adopt norms when a critical fraction of neighbors already hold them
- Parameters: `conformity_threshold`, `norm_stability_bonus`, `violation_penalty`

**Technology/innovation diffusion** — `backend/app/engine/templates/innovation.py`
- New ideas (inventions) appear stochastically based on agent exploration rate
- Innovations provide resource bonuses to adopters
- S-curve adoption pattern through network (slow start → rapid spread → saturation)
- Parameters: `innovation_rate`, `adoption_advantage`, `obsolescence_rate`

### 9.2 Mode-specific features
- **Temporal acceleration:** Configurable "years per step" framing (cosmetic but conceptually important)
- **Event log:** Track civilization milestones — "Institution X formed at step 42", "Norm Y adopted by 80% at step 67"
- **History view:** Timeline of institutional births, mergers, collapses alongside the force graph

### 9.3 Visualization preset
- Institutions rendered as translucent convex hulls around member agent clusters
- Node size grows with accumulated resource/influence over time
- "Civilization timeline" bar beneath the temporal slider showing key events
- Edge coloring: cooperation=green, conflict=red, trade=gold

### 9.4 Target use cases
- Policy scenario planning (how does a regulation reshape institutional landscape?)
- Strategy simulation (how do market structures evolve under competitive pressure?)
- Historical modeling (initialize from historical entities, see if known outcomes emerge)

---

## Phase 10: Digital Ecosystem of Minds Mode

**Goal:** Model cognition as an ecological process. Cognitive agents behave like species competing for resources (attention, memory, compute). Strategies evolve through variation and selection.

### 10.1 Additional templates

**Cognitive ecology** — `backend/app/engine/templates/cognitive_ecology.py`
- Agents have cognitive "phenotypes": persuasion ability, learning rate, deception tendency, cooperation tendency
- Phenotypes determine interaction outcomes (who gains resources from an exchange)
- Population dynamics: successful strategies reproduce (new agents spawn with similar phenotypes + mutation)
- Failing strategies go extinct (agents with zero resources are removed)
- Parameters: `reproduction_threshold`, `extinction_threshold`, `phenotype_mutation_std`
- Priors from evolutionary ecology (Robert May, population dynamics)

**Attention economy** — `backend/app/engine/templates/attention.py`
- Attention is a finite, shared resource
- Ideas compete for attention; agents allocate attention based on novelty and relevance
- Attention concentration follows power-law dynamics (winner-takes-most)
- Parameters: `total_attention_pool`, `novelty_weight`, `recency_decay`

**Cognitive heterogeneity** — `backend/app/engine/templates/cognitive_types.py`
- Agents classified into cognitive archetypes: heuristic thinkers, probabilistic reasoners, ideological rule-followers, strategic planners (per Herbert Simon's bounded rationality)
- Each archetype responds differently to information: heuristic agents follow trends, strategic agents game the system
- Archetype distribution in the population shifts based on relative success
- Parameters: `archetype_weights`, `strategy_switch_probability`

### 10.2 Mode-specific features
- **Population tracking:** Birth/death events, population size over time, species diversity index
- **Phylogenetic view:** Tree diagram showing lineage of cognitive strategies over time
- **Extinction alerts:** Highlight when a strategy type disappears from the population

### 10.3 Visualization preset
- Node color = cognitive archetype (4 distinct colors)
- Node size = resource level (shrinking nodes are endangered)
- "Extinction pulse" animation when an agent is removed
- Background heatmap showing attention density across the idea space
- Population bar chart sidebar showing archetype distribution

### 10.4 Target use cases
- Platform design testing (how do moderation rules change the cognitive ecology?)
- Misinformation analysis (which cognitive strategies are most susceptible?)
- Market microstructure (how do trading strategies compete and evolve?)

---

## Phase 11: Memetic Physics Mode

**Goal:** Treat ideas as particles obeying dynamics analogous to physics. Measure "force", "mass", and "entropy" of memes as they propagate through conceptual fields.

### 11.1 Additional templates

**Memetic field dynamics** — `backend/app/engine/templates/memetic_field.py`
- Ideas exist in an N-dimensional conceptual space (dimensions = topic axes extracted from documents)
- Each idea exerts an "attractive force" proportional to its energy and inversely proportional to conceptual distance
- Agents are pulled through conceptual space by the combined forces of nearby ideas
- Clusters form "ideological gravity wells" where agents accumulate
- Parameters: `field_strength`, `conceptual_friction`, `escape_velocity`

**Memetic energy conservation** — `backend/app/engine/templates/memetic_energy.py`
- Total "memetic energy" in the system is conserved (or slowly injected/dissipated)
- When an idea spreads, it drains energy from competing ideas (zero-sum attention)
- Energy can circulate through feedback loops, creating narrative cycles — ideas that periodically resurface
- Parameters: `total_energy`, `injection_rate`, `dissipation_rate`, `transfer_efficiency`

**Cultural mutation and inheritance** — `backend/app/engine/templates/cultural_evolution.py`
- Ideas have transmissibility, stability, mutation rate, and compatibility attributes
- When agents transmit ideas, the copy may mutate (content drift)
- Compatible ideas recombine into new hybrid ideas
- Over time, cultural lineages (families of related ideas) emerge
- Parameters: `mutation_rate`, `recombination_probability`, `compatibility_threshold`
- Priors from memetics (Richard Dawkins) and cultural evolution research

### 11.2 Mode-specific features
- **Memetic field map:** 2D projection of the conceptual space showing force vectors and gravity wells
- **Energy flow Sankey diagram:** Track how memetic energy flows between idea clusters
- **Phylogenetic tree of ideas:** Show how ideas mutate and branch over time
- **"Physics dashboard":** Display energy, entropy, temperature, pressure analogues

### 11.3 Visualization preset
- Nodes positioned by conceptual space coordinates (not force-directed layout — use the actual ideological dimensions)
- Idea nodes glow with intensity proportional to energy
- Gradient contour lines showing the memetic field (like a topographic map of idea attraction)
- Animated flow lines showing energy transfer between ideas
- Agent nodes shown as smaller dots drifting through the field

### 11.4 Target use cases
- Narrative analysis (how do competing narratives interact and evolve?)
- Campaign planning (where are the ideological gravity wells? how to shift them?)
- Cultural forecasting (which memes are gaining energy? which are decaying?)

---

## Phase 12: Market Dynamics Mode

**Goal:** Model economic systems — price formation, competitive dynamics, supply chains, and market structure evolution. Covers business strategy, financial modeling, and economic policy analysis.

### 12.1 Additional templates

**Market clearing** — `backend/app/engine/templates/market_clearing.py`
- Agents are buyers and sellers with reservation prices and inventories
- Prices adjust toward equilibrium via tâtonnement (iterative price adjustment)
- Supports multiple goods/markets with cross-elasticity effects
- Parameters: `price_adjustment_speed`, `elasticity`, `transaction_cost`
- Priors from microeconomics (Walrasian equilibrium, double auction experiments)

**Competitive dynamics** — `backend/app/engine/templates/competitive.py`
- Firms (Institution nodes) compete for market share (Resource nodes)
- Market share shifts based on relative quality, price, and network effects
- Includes entry/exit: new firms spawn when profit margins are high, failing firms exit
- Winner-takes-most dynamics when network effects are strong
- Parameters: `network_effect_strength`, `entry_barrier`, `exit_threshold`, `quality_weight`

**Supply chain flow** — `backend/app/engine/templates/supply_chain.py`
- Directed resource flow through multi-tier production networks
- Nodes represent suppliers, manufacturers, distributors, consumers
- Edges represent material/information flows with lead times and capacity constraints
- Disruptions propagate through the chain (bullwhip effect)
- Parameters: `flow_capacity`, `lead_time`, `buffer_stock`, `disruption_probability`

### 12.2 Mode-specific features
- **Market dashboard:** Price charts, market share pie charts, supply/demand curves
- **Equilibrium detector:** Highlight when markets approach or diverge from equilibrium
- **Disruption simulator:** Inject supply shocks, demand spikes, or regulatory changes mid-simulation
- **Profit/loss tracking:** Per-agent financial performance over time

### 12.3 Visualization preset
- Firms/institutions sized by market share
- Resource flow shown as animated streams between supply chain nodes (thickness = volume)
- Price encoded as node color gradient (red=high, blue=low)
- Market boundary regions shown as background zones
- Edge labels showing transaction volume

### 12.4 Target use cases
- Competitive strategy (what happens if a new entrant disrupts the market?)
- Supply chain resilience (how does a disruption at node X cascade?)
- Pricing strategy simulation (what's the equilibrium under different cost structures?)
- Economic policy impact (how does a tariff reshape trade flows?)
- Startup ecosystem modeling (when do network effects create winner-takes-all?)

---

## Phase 13: Public Discourse Mode

**Goal:** Model democratic deliberation, electoral dynamics, coalition formation, and policy feedback loops. Covers political science, public policy, and governance simulation.

### 13.1 Additional templates

**Electoral dynamics** — `backend/app/engine/templates/electoral.py`
- Agents have political preferences (multi-dimensional ideological positions)
- Candidates (special Agent nodes) position themselves to attract voter support
- Voting follows probabilistic rules: proximity-based + identity-based + momentum-based
- Strategic voting: agents may vote for non-preferred candidate to block a worse outcome
- Parameters: `voting_rule` (plurality/ranked/approval), `strategic_voting_rate`, `identity_weight`
- Priors from spatial voting theory (Hotelling, Downs)

**Coalition formation** — `backend/app/engine/templates/coalition.py`
- Agents form coalitions around shared interests or ideological proximity
- Coalitions have bargaining power proportional to size and cohesion
- Coalition stability depends on whether members benefit more inside than outside
- Coalitions can split when internal disagreements exceed a threshold
- Parameters: `coalition_benefit_multiplier`, `defection_temptation`, `minimum_viable_size`
- Priors from cooperative game theory (Shapley value, core stability)

**Deliberation dynamics** — `backend/app/engine/templates/deliberation.py`
- Agents exchange arguments (Idea nodes with evidence strength and persuasiveness)
- Argument quality matters: well-supported arguments shift opinions more than repetition alone
- Echo chambers form when agents selectively engage with agreeable arguments
- Deliberation quality metric: tracks whether the group converges on well-supported positions or on popular but unsupported ones
- Parameters: `evidence_weight`, `confirmation_bias`, `argument_decay`, `engagement_selectivity`

### 13.2 Mode-specific features
- **Election simulator:** Run elections at configurable intervals during the simulation
- **Coalition map:** Visual overlay showing which agents belong to which coalition
- **Deliberation quality tracker:** Are debates improving group knowledge or just amplifying noise?
- **Policy outcome predictor:** Given final opinion distributions, project likely policy support levels
- **Overton window visualizer:** Track which ideas are considered mainstream vs fringe over time

### 13.3 Visualization preset
- Agents positioned by ideological coordinates (left-right, authoritarian-libertarian, etc.)
- Coalition boundaries as colored regions
- Argument flow shown as directed edges with thickness = persuasiveness
- Candidate nodes highlighted with voter share halos
- "Overton window" shown as a translucent band that shifts over time

### 13.4 Target use cases
- Electoral forecasting (how do different voting systems change outcomes?)
- Policy deliberation (does a citizens' assembly converge on good policy?)
- Polarization analysis (what conditions produce echo chambers vs. productive debate?)
- Coalition stability (which political alliances are fragile?)
- Public opinion simulation (how does a scandal or crisis reshape the discourse?)

---

## Phase 14: Knowledge Ecosystems Mode

**Goal:** Model the production, validation, and propagation of knowledge — scientific discovery, peer review, paradigm shifts, and technology adoption. Covers science, R&D, and tech innovation dynamics.

### 14.1 Additional templates

**Knowledge production** — `backend/app/engine/templates/knowledge_production.py`
- Agents (researchers) explore a knowledge landscape with multiple possible discoveries
- Discovery probability depends on: agent skill, current knowledge frontier, and collaboration with neighbors
- Knowledge builds cumulatively: later discoveries require earlier ones as prerequisites (dependency graph)
- "Standing on the shoulders of giants" effect: well-connected agents discover faster
- Parameters: `discovery_probability`, `prerequisite_depth`, `collaboration_bonus`, `serendipity_rate`

**Peer review and validation** — `backend/app/engine/templates/peer_review.py`
- New ideas must pass through a validation process before becoming "accepted knowledge"
- Reviewer agents evaluate ideas based on evidence strength and consistency with existing knowledge
- False positives (bad ideas accepted) and false negatives (good ideas rejected) both occur
- Replication dynamics: accepted ideas are periodically re-tested
- Parameters: `reviewer_accuracy`, `replication_rate`, `retraction_threshold`, `novelty_bias`
- Priors from science of science research (meta-science, replication crisis studies)

**Paradigm dynamics** — `backend/app/engine/templates/paradigm.py`
- Knowledge organizes into paradigms (Institution nodes representing dominant frameworks)
- Normal science: incremental knowledge accumulation within a paradigm
- Anomalies accumulate when observations contradict the paradigm
- Paradigm shift: when anomalies exceed a crisis threshold, a competing paradigm can take over
- Parameters: `anomaly_accumulation_rate`, `crisis_threshold`, `paradigm_inertia`, `switching_cost`
- Priors from philosophy of science (Thomas Kuhn's structure of scientific revolutions)

### 14.2 Mode-specific features
- **Knowledge frontier map:** Visualize which areas of the knowledge space have been explored vs. unexplored
- **Citation network:** Track which ideas cite/build on which others
- **Paradigm health monitor:** Anomaly count vs. crisis threshold for each active paradigm
- **Discovery timeline:** Chronological list of discoveries with their impact scores
- **h-index / impact tracker:** Per-agent productivity and influence metrics

### 14.3 Visualization preset
- Knowledge space as a 2D map with explored regions lit and unexplored regions dark
- Paradigms as large background regions with competing paradigms shown in contrasting colors
- Discovery nodes pulse when created, grow as they accumulate citations
- Citation edges shown as thin directed lines (animate to show knowledge flow)
- Agent nodes clustered around the paradigm they follow

### 14.4 Target use cases
- R&D strategy (where should research investment be focused?)
- Science policy (how do funding structures affect discovery rates?)
- Technology forecasting (which technologies are approaching paradigm-shift potential?)
- Open-source ecosystem modeling (how does knowledge sharing accelerate innovation?)
- Peer review reform analysis (what happens if we change review processes?)

---

## Phase 15: Ecological Systems Mode

**Goal:** Model actual ecological dynamics — species interactions, habitat changes, ecosystem resilience, and environmental policy impact. Covers ecology, environmental science, and sustainability analysis.

### 15.1 Additional templates

**Population ecology** — `backend/app/engine/templates/population_ecology.py`
- Species (Agent/Resource node types) with birth rates, death rates, and carrying capacities
- Predator-prey dynamics: classic Lotka-Volterra extended to network topology
- Competition: species sharing resources deplete each other's carrying capacity
- Mutualism: some species enhance each other's fitness
- Parameters: `birth_rate`, `death_rate`, `carrying_capacity`, `predation_rate`, `mutualism_coefficient`
- Priors from quantitative ecology (well-studied parameter ranges for many species)

**Habitat dynamics** — `backend/app/engine/templates/habitat.py`
- Environment nodes represent habitats with quality, area, and connectivity attributes
- Habitat quality changes over time due to species activity, external stressors, or restoration
- Fragmentation: when habitat connectivity drops below threshold, isolated populations decline
- Migration: species move between habitats based on quality gradients
- Parameters: `degradation_rate`, `restoration_rate`, `connectivity_threshold`, `migration_sensitivity`

**Ecosystem services** — `backend/app/engine/templates/ecosystem_services.py`
- Map ecological states to human-relevant services (water purification, carbon sequestration, pollination, etc.)
- Service output depends on species composition and habitat quality
- Economic valuation: assign monetary proxies to services for policy analysis
- Tipping points: service provision can collapse non-linearly when biodiversity drops below critical thresholds
- Parameters: `service_coefficients`, `biodiversity_threshold`, `valuation_model`

### 15.2 Mode-specific features
- **Biodiversity index:** Track species richness, Shannon entropy, and evenness over time
- **Food web visualizer:** Interactive trophic network showing energy flow
- **Habitat connectivity map:** Spatial layout showing habitat patches and corridors
- **Tipping point alerts:** Warn when ecosystem approaches critical thresholds
- **Scenario comparisons:** Conservation vs. development vs. restoration trajectories

### 15.3 Visualization preset
- Habitat nodes as large background regions with color = habitat quality (green=healthy, brown=degraded)
- Species nodes sized by population, colored by trophic level (producers=green, consumers=blue, predators=red)
- Predation/competition edges with animated energy flow
- Seasonal cycle option: parameters oscillate to simulate annual patterns
- "Ecosystem health" gauge showing aggregate resilience score

### 15.4 Target use cases
- Conservation planning (which species/habitats are most critical to protect?)
- Environmental impact assessment (how does a development project cascade through the ecosystem?)
- Climate adaptation (how do species range shifts affect ecosystem services?)
- Restoration prioritization (where does investment produce the most ecological benefit?)
- Sustainability policy (what are the tipping points we must avoid?)

---

## Phase 16: Extended Templates & Custom Equations

**Goal:** Expand the template library and allow users to define their own dynamical equations.

### 16.1 Additional template families

**Contagion models** — `backend/app/engine/templates/contagion.py`
- SIR/SIS/SEIR epidemic-style spreading on networks
- Useful for modeling viral content, adoption cascades, panic propagation
- Parameters: `infection_rate`, `recovery_rate`, `immunity_duration`

**Game-theoretic dynamics** — `backend/app/engine/templates/game_theory.py`
- Agents play repeated games (prisoner's dilemma, coordination, hawk-dove)
- Strategy updates via imitation dynamics or best-response
- Parameters: `payoff_matrix`, `update_rule`, `noise`

**Network evolution** — `backend/app/engine/templates/network_evolution.py`
- The graph topology itself evolves: agents form/break connections based on homophily, reciprocity, or triadic closure
- Parameters: `rewiring_probability`, `homophily_strength`, `triadic_closure_rate`

**Memory landscapes** — `backend/app/engine/templates/memory_landscape.py`
- Shared cultural memory as a global field that agents read from and write to
- Popular memories gain inertia; forgotten ideas fade
- Old ideas can resurface when conditions change (historical layering)
- Parameters: `memory_persistence`, `retrieval_threshold`, `resonance_amplification`

### 16.2 Custom equation editor
- **`frontend/src/components/CustomEquationEditor.vue`** — UI for defining update rules
- Simple DSL or Python-expression input: e.g., `node.energy += sum(neighbors.energy * edge.weight) * param.transfer_rate - node.energy * param.decay`
- Backend parses and validates the expression, wraps it in a DynamicsTemplate
- Sandboxed execution (restricted eval or AST-based interpreter) for safety
- Save/load custom templates per project

### 16.3 Template marketplace (future)
- Users can publish custom templates
- Community-contributed domain-specific templates (epidemiology, finance, ecology)
- Rating and validation metrics for template quality

---

## Phase 17: Advanced Visualization & Analysis

**Goal:** Level up the visual spectacle and analytical capabilities.

### 17.1 Multi-view visualization
- Split-screen: force graph + field map + timeline simultaneously
- Synchronized scrubbing across all views
- Comparison mode: run two simulations with different parameters side-by-side

### 17.2 3D visualization (optional WebGL upgrade)
- Three.js rendering for memetic field mode (3D conceptual space)
- Fly-through camera for exploring large simulation worlds
- Particle systems for energy flows

### 17.3 Scenario comparison & backtesting
- Run multiple simulations with parameter sweeps (Monte Carlo exploration)
- Compare outcome distributions across scenarios
- Backtest against historical data when available
- Report agent integrates dynamics metrics into analysis

### 17.4 Export & sharing
- Export simulation as shareable interactive HTML (bundled D3 visualization)
- Export data as CSV/JSON for external analysis
- Embeddable widget for presentations
- GIF/video recording of simulation replays

---

## Full Roadmap Summary

```
MVP (Phases 1–7): Unified Engine
│
│  Delivers: typed graphs, 5 base templates, metrics layer,
│  D3 force visualization, OASIS bridge, API
│
├── Phase 8: Mode Framework           ← Abstraction for curated experiences
│
│   ┌── Simulation Modes (all parallel after Phase 8) ──────────────────────┐
│   │                                                                       │
│   ├── Phase 9:  Synthetic Civilizations  ← Institutional emergence,      │
│   │       Templates: institutional.py, norms.py, innovation.py            │
│   │                                                                       │
│   ├── Phase 10: Digital Ecosystem        ← Cognitive ecology, attention   │
│   │       Templates: cognitive_ecology.py, attention.py, cognitive_types.py│
│   │                                                                       │
│   ├── Phase 11: Memetic Physics          ← Idea fields, energy, culture  │
│   │       Templates: memetic_field.py, memetic_energy.py,                 │
│   │                  cultural_evolution.py                                 │
│   │                                                                       │
│   ├── Phase 12: Market Dynamics          ← Pricing, competition, supply  │
│   │       Templates: market_clearing.py, competitive.py, supply_chain.py  │
│   │                                                                       │
│   ├── Phase 13: Public Discourse         ← Elections, coalitions, debate │
│   │       Templates: electoral.py, coalition.py, deliberation.py          │
│   │                                                                       │
│   ├── Phase 14: Knowledge Ecosystems     ← Discovery, peer review,      │
│   │       Templates: knowledge_production.py, peer_review.py, paradigm.py │
│   │                                                                       │
│   └── Phase 15: Ecological Systems       ← Species, habitats, services  │
│           Templates: population_ecology.py, habitat.py,                   │
│                      ecosystem_services.py                                │
│                                                                           │
├── Phase 16: Extended Templates      ← Contagion, game theory, network    │
│       + Custom Equation Editor         evolution, memory landscapes,      │
│                                        user-defined equations             │
│                                                                           │
└── Phase 17: Advanced Visualization  ← 3D, multi-view, scenario          │
        + Analysis                       comparison, backtesting, export    │
```

│
│   ┌── Launch & Virality (sequential, after MVP + at least 2 modes) ───────┐
│   │                                                                       │
│   ├── Phase 18: Demo Scenarios       ← 5 pre-run demos with saved data   │
│   │                                                                       │
│   ├── Phase 19: Screenshot Pipeline  ← Hero images, GIFs, architecture   │
│   │                                     diagrams, automated capture       │
│   │                                                                       │
│   ├── Phase 20: README & Docs        ← EN, 简体中文, 繁體中文, 日本語      │
│   │              (Multilingual)         Viral copy, visual-first layout    │
│   │                                                                       │
│   ├── Phase 21: Demo Site            ← GitHub Pages, zero-install demo,  │
│   │              (GitHub Pages)         Vue.js static site, <3s load      │
│   │                                                                       │
│   └── Phase 22: Launch Strategy      ← Coordinated multi-platform push,  │
│                                         GitHub Trending mechanics,        │
│                                         EN/CN/JP community seeding        │
│   └───────────────────────────────────────────────────────────────────────┘
```

**Dependencies:**
- Phases 9–15 (all modes) can be built in any order or in parallel once Phase 8 is complete.
- Phase 16 can begin as soon as the base template interface (Phase 3) is stable.
- Phase 17 is independent and can be developed alongside any post-MVP phase.
- **Phases 18–22 (launch) should begin after the MVP (Phases 1–7) plus at least 2 modes are working.** Don't wait for all 7 modes — launch with the most visually compelling ones first (likely Memetic Physics + Synthetic Civilizations).
- Phase 18 (demos) must come before Phase 19 (screenshots) which must come before Phase 20 (README) which must come before Phase 21 (demo site) which must come before Phase 22 (launch). These are sequential.

**Domain coverage:**
| Domain | Primary Mode(s) | Supporting Modes |
|---|---|---|
| Business | Market Dynamics (12) | Synthetic Civ (9), Digital Ecosystem (10) |
| Policy/Politics | Public Discourse (13) | Synthetic Civ (9), Memetic Physics (11) |
| Science/Tech | Knowledge Ecosystems (14) | Digital Ecosystem (10), Market Dynamics (12) |
| Humanities/Culture | Memetic Physics (11) | Public Discourse (13), Synthetic Civ (9) |
| Ecology/Environment | Ecological Systems (15) | Market Dynamics (12) for policy impact |
| Social/Cultural | Synthetic Civ (9), Digital Ecosystem (10) | Memetic Physics (11) |

---

## Verification Strategy

### Unit tests
- Graph model: CRUD, circularity detection, snapshot round-trip
- Each template: 3-node graph with known expected output
- Metrics: synthetic graphs with known metric values
- Persistence: save/load integrity

### Integration tests
- OASIS bridge: feed sample action JSONL → verify graph updates
- Engine runner: 100-step simulation → verify metrics converge/diverge as expected
- API: full CRUD lifecycle through REST endpoints

### End-to-end test
1. Upload a sample policy document (e.g., a short article about social media regulation)
2. System extracts entities and builds typed graph
3. System suggests relevant templates (likely Opinion + Diffusion)
4. Run OASIS simulation + dynamics engine for 50 steps
5. Open DynamicsView → verify force graph renders with correct node types
6. Scrub timeline → verify snapshots replay correctly
7. Check metrics dashboard → verify time series charts populate
8. Verify no regressions in original MiroFish workflow

---

## Launch & Virality Strategy

The phases below are not afterthoughts — they are as critical as the engine itself. MiroFish went viral because of narrative packaging, visual spectacle, and accessibility, not code quality. Memetic Flow must ship with equally compelling presentation from day one.

---

## Phase 18: Demo Scenarios & Pre-Run Data

**Goal:** Create 3–5 compelling pre-run simulation demos that showcase each flagship mode. Users should be able to see results immediately without configuring anything or spending API credits.

### 18.1 Demo scenario selection
Choose scenarios that are immediately legible, emotionally engaging, and demonstrate emergent behavior:

| Demo | Mode | Input Document | Why It's Compelling |
|---|---|---|---|
| **"Social Media Regulation"** | Public Discourse + Memetic Physics | Draft of a platform regulation bill | Watch polarization form in real time, see coalitions crystallize, observe how narratives compete |
| **"AI Startup Ecosystem"** | Market Dynamics + Knowledge Ecosystems | Tech industry landscape report | Watch companies compete, paradigm shifts emerge, winner-takes-all dynamics form |
| **"Amazon Deforestation"** | Ecological Systems | Environmental impact assessment | Watch tipping points approach, ecosystem services collapse, species cascade |
| **"Civilization from Scratch"** | Synthetic Civilizations | Simple resource/geography description | Watch institutions, norms, and trade emerge from nothing — the "wow" demo |
| **"Meme War"** | Memetic Physics + Digital Ecosystem | Viral social media event | Watch ideas gain energy, gravity wells form, cognitive strategies compete |

### 18.2 Pre-run data generation
- Run each demo scenario locally with fixed random seeds for reproducibility
- Save complete simulation outputs: all graph snapshots, metric time series, phase transition events
- Package as JSON bundles in `demo/data/{scenario_name}/`
- Demo site loads these bundles directly — no backend or API calls needed

### 18.3 Demo data structure
```
demo/data/
├── social_media_regulation/
│   ├── metadata.json          # Scenario description, mode, templates used
│   ├── initial_graph.json     # Starting typed graph
│   ├── snapshots.json         # All timestep snapshots (compressed)
│   ├── metrics.json           # Metric time series
│   ├── events.json            # Phase transitions and milestones
│   └── report_summary.md      # Generated report excerpt
├── ai_startup_ecosystem/
│   └── ...
├── amazon_deforestation/
│   └── ...
├── civilization_from_scratch/
│   └── ...
└── meme_war/
    └── ...
```

### 18.4 Verification
- Each demo loads in <2 seconds on the demo site
- All visualizations render correctly from pre-run data
- Temporal slider replays the full simulation smoothly

---

## Phase 19: Screenshot & Visual Asset Pipeline

**Goal:** Generate the high-impact visual assets needed for README, social media, and demo site. These images are what people actually see when deciding whether to star/share.

### 19.1 Hero screenshots (6–8 images)
Capture the most visually striking moments from demo simulations:

1. **Force graph with animated flows** — Full-screen graph showing hundreds of nodes with directed particle flow, institutional clusters, and color-coded types. This is the "money shot" — the image that makes people stop scrolling.
2. **Phase transition moment** — Before/after split showing a sudden polarization event or institutional collapse. Dramatic contrast.
3. **Memetic field map** — Topographic contour visualization with glowing idea nodes and gravity wells. Looks like nothing else on GitHub.
4. **Civilization timeline** — Institutions forming and collapsing over time with the force graph below. Tells a story.
5. **Metrics dashboard** — Clean line charts showing entropy, polarization, and Gini diverging at a critical moment.
6. **Mode selector** — The card-based UI showing all 7 modes. Communicates breadth.
7. **Document upload → graph** — Before/after showing a document transforming into a typed graph. Shows the pipeline.
8. **Side-by-side comparison** — Two simulations with different parameters producing different outcomes. Shows analytical power.

### 19.2 Animated GIFs (3–4)
Short looping animations are more shareable than static images:

1. **Simulation replay** (5–10s loop) — Force graph evolving over time with nodes moving, clusters forming, flows pulsing
2. **Phase transition cascade** (3–5s) — Sudden regime change rippling through the network
3. **Memetic field evolution** (5–10s) — Ideas gaining and losing energy, gravity wells shifting
4. **Full pipeline** (10–15s) — Document upload → graph extraction → simulation → visualization

### 19.3 Architecture diagram
- Clean SVG/PNG showing the 5-layer architecture (from the plan's ASCII diagram but professionally rendered)
- Use a tool like Excalidraw, Mermaid, or a design tool
- Must clearly show what's new vs. what's inherited from MiroFish

### 19.4 Automated screenshot script — `scripts/capture_screenshots.py`
- Uses Playwright or Selenium to navigate the demo, set up specific views, and capture screenshots
- Ensures consistent resolution (1920x1080 for hero images, 800x600 for inline)
- Outputs to `docs/screenshots/` with descriptive filenames
- Re-runnable whenever the UI changes

### 19.5 Asset locations
```
docs/
├── screenshots/
│   ├── hero_force_graph.png
│   ├── hero_phase_transition.png
│   ├── hero_memetic_field.png
│   ├── hero_civilization_timeline.png
│   ├── hero_metrics_dashboard.png
│   ├── hero_mode_selector.png
│   ├── hero_document_to_graph.png
│   └── hero_comparison.png
├── gifs/
│   ├── simulation_replay.gif
│   ├── phase_transition.gif
│   ├── memetic_field_evolution.gif
│   └── full_pipeline.gif
├── diagrams/
│   ├── architecture.svg
│   └── roadmap.svg
└── logos/
    ├── memetic_flow_logo.svg
    ├── memetic_flow_logo_dark.svg
    └── memetic_flow_banner.png
```

---

## Phase 20: README & Documentation (Multilingual)

**Goal:** Write READMEs that trigger the viral response. The README is the landing page — most people who star a repo never clone it. They star based on the README alone.

### 20.1 README structure (proven viral pattern)

Study MiroFish's README structure and improve on it. The pattern that works:

```
1. Hero banner image (logo + tagline)
2. One-sentence pitch (bold, philosophical)
3. Animated GIF showing the system in action
4. "What is this?" — 3–4 sentences max
5. Key features with screenshots (NOT bullet lists — visual cards)
6. Architecture diagram
7. Quick start (docker-compose up, 3 steps max)
8. Demo link (prominent, above the fold)
9. Mode gallery — visual cards for each simulation mode
10. Comparison table (Memetic Flow vs MiroFish vs others)
11. Roadmap (brief)
12. Citation / academic references
13. Contributing guide
14. License
```

### 20.2 Viral copy elements

**Tagline options** (test which resonates):
- "A physics engine for ideas."
- "Simulate the future. Understand the present."
- "Where complex systems become visible."
- "The laboratory for civilization."

**One-sentence pitch:**
> Memetic Flow transforms documents into living simulations — watch institutions emerge, ideas compete, ecosystems evolve, and markets form through dynamical equations grounded in complexity science.

**Key narrative hooks:**
- Frame as "the next step beyond MiroFish" — ride the existing attention wave
- Emphasize the shift from "agents chatting" to "systems dynamics" — positions as more scientific
- Reference the intellectual lineage explicitly (Asimov's psychohistory, complexity science, memetics)
- Highlight the visual spectacle — "watch civilizations emerge" is more compelling than "run agent simulations"

### 20.3 Multilingual versions

| File | Language | Audience |
|---|---|---|
| `README.md` | English | Default, international |
| `README-CN.md` | Simplified Chinese (简体中文) | Mainland China (primary GitHub trending audience for this category) |
| `README-TW.md` | Traditional Chinese (繁體中文) | Taiwan, Hong Kong, overseas Chinese dev communities |
| `README-JP.md` | Japanese (日本語) | Japan's active open-source and AI research community |

**Translation approach:**
- Do NOT machine-translate — adapt for each audience's tech culture
- Chinese versions should reference the MiroFish origin story (well-known in Chinese dev circles)
- Japanese version should reference relevant Japanese complexity science and AI agent research
- Each version gets localized screenshots if UI is localized, otherwise same screenshots with translated captions

### 20.4 Supporting documentation
```
docs/
├── QUICKSTART.md              # 5-minute setup guide
├── MODES.md                   # Detailed guide to each simulation mode
├── TEMPLATES.md               # Template library reference
├── CUSTOM_EQUATIONS.md        # Guide to writing custom templates
├── API.md                     # REST API reference
├── ARCHITECTURE.md            # Technical deep dive
├── CONTRIBUTING.md            # How to contribute
├── FAQ.md                     # Common questions
└── i18n/
    ├── QUICKSTART-CN.md
    ├── QUICKSTART-TW.md
    └── QUICKSTART-JP.md
```

### 20.5 Verification
- All READMEs render correctly on GitHub (preview before push)
- All images load (use relative paths, not absolute URLs)
- Quick start instructions actually work from a clean clone
- Links to demo site work

---

## Phase 21: Demo Site (GitHub Pages)

**Goal:** Build an interactive demo site at `{username}.github.io/memetic-flow/` that lets visitors experience the system without installing anything. This is the single most important virality driver — MiroFish's demo site is what converts curious visitors into stars.

### 21.1 Demo site architecture

```
Static site (no backend needed)
├── Landing page
│   ├── Hero section with animated background (subtle force graph animation)
│   ├── One-line pitch + "Try it now" button
│   └── Feature cards with screenshots
├── Interactive demo
│   ├── Scenario picker (5 pre-run demos)
│   ├── Full DynamicsGraphPanel with pre-loaded data
│   ├── Temporal slider for replaying simulation
│   ├── Metrics dashboard
│   ├── Mode info panel explaining what's happening
│   └── "Run your own" CTA → links to repo quickstart
├── Mode gallery
│   ├── Visual card for each of the 7 modes
│   ├── Click to see that mode's demo scenario
│   └── Template descriptions and parameter explanations
├── Architecture page
│   ├── Interactive architecture diagram
│   ├── "How it works" walkthrough
│   └── Comparison with MiroFish
└── Footer
    ├── GitHub link (prominent star button)
    ├── Citation info
    └── Social links
```

### 21.2 Tech stack for demo site
- **Framework:** Vue.js 3 (reuse frontend components directly from the main project)
- **Build:** Vite with static site generation
- **Hosting:** GitHub Pages (free, automatic deployment via GitHub Actions)
- **Data:** Pre-run simulation bundles loaded as static JSON
- **Visualization:** Same D3.js components from the main app — ensures demo matches the real product

### 21.3 Key UX requirements
- **< 3 second load time** — first impression must be instant
- **No signup, no API key, no installation** — zero friction
- **Mobile responsive** — many first visitors come from Twitter/WeChat on phones
- **Immediate visual impact** — the force graph should be animating within 1 second of page load
- **Guided experience** — first-time visitors get a brief overlay explaining what they're seeing
- **Shareable URLs** — each demo scenario has its own URL for social sharing

### 21.4 Demo site files
```
demo/
├── index.html
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── views/
│   │   ├── Landing.vue
│   │   ├── DemoPlayer.vue
│   │   ├── ModeGallery.vue
│   │   └── Architecture.vue
│   ├── components/
│   │   ├── HeroSection.vue
│   │   ├── ScenarioPicker.vue
│   │   ├── FeatureCards.vue
│   │   └── ... (reuse from main frontend)
│   └── data/               # Symlinked or copied from demo/data/
├── vite.config.js
├── package.json
└── .github/
    └── workflows/
        └── deploy-demo.yml  # GitHub Actions: build + deploy to Pages
```

### 21.5 GitHub Actions for auto-deployment
```yaml
# .github/workflows/deploy-demo.yml
# Triggers on push to main branch
# Builds demo site with Vite
# Deploys to GitHub Pages
# Includes cache-busting for screenshots/GIFs
```

### 21.6 Verification
- Demo site loads in <3s on 3G connection
- All 5 demo scenarios play correctly
- Temporal slider works smoothly
- Mobile layout is usable
- GitHub star button is visible and functional
- Social share meta tags (Open Graph) produce attractive previews when shared

---

## Phase 22: Launch & Distribution Strategy

**Goal:** Maximize the probability of hitting GitHub Trending and generating social media amplification. Timing, platform strategy, and community seeding all matter.

### 22.1 Pre-launch checklist
- [ ] All 5 demo scenarios working on demo site
- [ ] README with hero screenshots and GIFs renders perfectly
- [ ] All 4 language READMEs complete and reviewed by native speakers
- [ ] Quick start works from clean clone (tested on macOS, Linux, WSL)
- [ ] Demo site loads fast and looks polished
- [ ] GitHub repo metadata: description, topics, website URL all set
- [ ] GitHub topics: `ai-agents`, `simulation`, `complex-systems`, `forecasting`, `multi-agent`, `llm`, `d3js`, `visualization`, `memetics`, `complexity-science`

### 22.2 GitHub Trending mechanics
GitHub Trending is driven by **star velocity** — stars per unit time, not total stars. The algorithm favors:
- Burst of stars in first 24–48 hours
- Stars from diverse accounts (not bots)
- Repository activity (recent commits, issues, PRs)

**Strategy:**
- Coordinate launch across platforms simultaneously
- Post at optimal times: Tuesday–Thursday, morning US / evening China (overlapping peak hours)
- Ensure the repo has recent commit activity in the days before launch

### 22.3 Platform-specific launch posts

**GitHub:** Polish the README — this IS the launch post for GitHub visitors.

**Twitter/X:**
- Thread format: hook → GIF → explanation → demo link → repo link
- Hook: "We built a physics engine for ideas. Upload any document. Watch civilizations emerge." + animated GIF
- Tag relevant accounts: AI researchers, complexity science accounts, MiroFish creator
- Use hashtags: #AI #LLM #AgentSimulation #ComplexSystems

**Reddit:**
- r/MachineLearning: Technical framing, emphasize the dynamical systems innovation
- r/artificial: Broader framing, emphasize the "simulate the future" angle
- r/dataisbeautiful: Lead with the visualization, post the best GIF
- r/compsci: Emphasize the complexity science foundations

**Hacker News:**
- "Show HN: Memetic Flow – A dynamics engine for simulating complex social systems"
- Lead with the technical innovation (template equations, not just LLM agents)
- HN audience values substance over hype — emphasize the mathematical grounding

**Chinese platforms (critical for star velocity):**
- WeChat tech groups and public accounts (公众号)
- Zhihu (知乎): Long-form technical post explaining the architecture
- Juejin (掘金): Developer-focused writeup
- V2EX: Technical community post
- CSDN: Tutorial-style post with code examples
- Frame as "MiroFish的下一步进化" (the next evolution of MiroFish) — ride existing awareness

**Japanese platforms:**
- Qiita: Technical article with code walkthrough
- Zenn: More conceptual/architectural discussion
- Twitter JP AI community

### 22.4 Content calendar
```
Day -7:  Final polish, native speaker review of all READMEs
Day -3:  Soft launch to 5–10 trusted developers for feedback
Day -1:  Fix any issues from soft launch, final screenshot refresh
Day 0:   Simultaneous launch across all platforms (coordinate timezone)
         - GitHub README finalized
         - Twitter thread posted
         - Reddit posts (stagger by 1–2 hours across subreddits)
         - HN Show HN posted
         - Chinese platform posts
         - Japanese platform posts
Day +1:  Monitor and respond to all comments/issues quickly
         - Engagement in first 24h is critical for Trending
         - Fix any bugs users report immediately
Day +2:  Post follow-up content (architecture deep dive, mode walkthrough)
Day +7:  Write a retrospective blog post if the launch succeeds
```

### 22.5 Community engagement
- Respond to every GitHub issue within 2 hours during launch week
- Create "good first issue" labels for contributors
- Welcome PRs for new templates and modes
- Create a Discord or GitHub Discussions space for the community

### 22.6 Verification
- All platform posts are drafted and reviewed before Day 0
- Demo site is stable under concurrent load
- Quick start instructions verified on fresh machines
- All README images load correctly from GitHub CDN
