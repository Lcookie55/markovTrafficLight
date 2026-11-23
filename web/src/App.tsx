import { useEffect, useState } from 'react'
import { getConfig } from './api'
import BenchmarkView from './BenchmarkView'
import LiveView from './LiveView'
import PolicyView from './PolicyView'
import type { ScenarioJson } from './types'
import { useSim } from './useSim'

type Tab = 'live' | 'policy' | 'benchmark'
const TABS: { id: Tab; label: string }[] = [
  { id: 'live', label: 'Live simulation' },
  { id: 'policy', label: 'Policy explorer' },
  { id: 'benchmark', label: 'Benchmark' },
]

export default function App() {
  const sim = useSim()
  const [tab, setTab] = useState<Tab>('live')
  const [scenarios, setScenarios] = useState<ScenarioJson[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getConfig().then(r => setScenarios(r.scenarios))
      .catch(() => setError('Cannot reach the API. Start it with: uvicorn api.main:app --port 8000'))
  }, [])

  const mdpFrame = sim.state.latest['mdp'] ?? sim.state.latest['mdp_nominal']

  return (
    <div className="app">
      <header>
        <h1>Smart Traffic Light <span>Markov Decision Process</span></h1>
        <nav aria-label="Views" role="tablist">
          {TABS.map(t => (
            <button key={t.id} role="tab" aria-selected={tab === t.id}
              className={tab === t.id ? 'tab active' : 'tab'} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {error && <p className="err" role="alert">{error}</p>}
        {scenarios.length > 0 && (
          <>
            <div hidden={tab !== 'live'}><LiveView sim={sim} scenarios={scenarios} /></div>
            {tab === 'policy' && <PolicyView scenarios={scenarios} currentState={mdpFrame?.state_idx ?? null} />}
            {tab === 'benchmark' && <BenchmarkView />}
          </>
        )}
      </main>
      <footer>
        Four-way intersection &middot; 96-state MDP &middot; &Delta;t = 5 s &middot; Value Iteration, &gamma; = 0.95
      </footer>
    </div>
  )
}
