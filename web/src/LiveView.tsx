import { useEffect, useRef, useState } from 'react'
import { SeriesChart } from './Charts'
import IntersectionCanvas from './IntersectionCanvas'
import type { ScenarioJson } from './types'
import { CONTROLLER_COLOR, CONTROLLER_LABEL } from './types'
import type { useSim } from './useSim'

const SPEEDS = [1, 2, 5, 10, 25, 50, 100]
const LEVELS = ['0', '1–3', '4–7', '8+']

type Sim = ReturnType<typeof useSim>

export default function LiveView({ sim, scenarios }: { sim: Sim; scenarios: ScenarioJson[] }) {
  const { state } = sim
  const [scenarioId, setScenarioId] = useState('S3')
  const [seed, setSeed] = useState(1)
  const [speed, setSpeed] = useState(10)
  const [ctrlA, setCtrlA] = useState('mdp')
  const [ctrlB, setCtrlB] = useState('fixed')
  const [lamNs, setLamNs] = useState(0.3)
  const [lamEw, setLamEw] = useState(0.08)
  const [customized, setCustomized] = useState(false)
  const debounce = useRef<number | undefined>(undefined)

  const scenario = scenarios.find(s => s.id === scenarioId)
  useEffect(() => {
    if (scenario) { setLamNs(scenario.lam_ns); setLamEw(scenario.lam_ew); setCustomized(false) }
  }, [scenario])

  const active = state.status === 'running' || state.status === 'connecting'
  const runStarted = state.status !== 'idle'

  const start = () => {
    const controllers = ctrlA === ctrlB ? [ctrlA] : [ctrlA, ctrlB]
    sim.start({
      scenario: scenarioId, seed, controllers, speed,
      ...(customized ? { lam_ns: lamNs, lam_ew: lamEw } : {}),
    })
  }

  const onLambda = (ns: number, ew: number) => {
    setLamNs(ns); setLamEw(ew); setCustomized(true)
    if (state.status === 'running') {
      window.clearTimeout(debounce.current)
      debounce.current = window.setTimeout(() => sim.setLambda(ns, ew), 150)
    }
  }

  const onSpeed = (v: number) => { setSpeed(v); sim.setSpeed(v) }
  const stepMs = (state.config?.dt ?? 5) * 1000 / speed
  const names = state.controllers.length ? state.controllers : [ctrlA, ctrlB].filter((c, i, a) => a.indexOf(c) === i)
  const horizon = state.config?.horizon ?? 3600
  const mm = (t: number) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`

  return (
    <div className="live">
      <section className="card controls" aria-label="Simulation controls">
        <div className="field">
          <label htmlFor="scn">Scenario</label>
          <select id="scn" value={scenarioId} onChange={e => setScenarioId(e.target.value)}>
            {scenarios.map(s => <option key={s.id} value={s.id}>{s.id} – {s.name}</option>)}
          </select>
          <p className="hint">{scenario?.description}</p>
        </div>
        <div className="field">
          <label htmlFor="seed">Random seed</label>
          <input id="seed" type="number" min={0} value={seed} onChange={e => setSeed(Number(e.target.value))} />
        </div>
        <div className="field">
          <label htmlFor="ca">Left panel</label>
          <select id="ca" value={ctrlA} onChange={e => setCtrlA(e.target.value)}>
            {Object.entries(CONTROLLER_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <label htmlFor="cb">Right panel</label>
          <select id="cb" value={ctrlB} onChange={e => setCtrlB(e.target.value)}>
            {Object.entries(CONTROLLER_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="spd">Speed: {speed}&times;</label>
          <input id="spd" type="range" min={0} max={SPEEDS.length - 1} step={1}
            value={SPEEDS.indexOf(speed)} onChange={e => onSpeed(SPEEDS[Number(e.target.value)])} />
        </div>
        <div className="field">
          <label htmlFor="lns">&lambda; North&ndash;South: {lamNs.toFixed(2)} veh/s per approach</label>
          <input id="lns" type="range" min={0} max={0.5} step={0.01} value={lamNs}
            onChange={e => onLambda(Number(e.target.value), lamEw)} />
          <label htmlFor="lew">&lambda; East&ndash;West: {lamEw.toFixed(2)} veh/s per approach</label>
          <input id="lew" type="range" min={0} max={0.5} step={0.01} value={lamEw}
            onChange={e => onLambda(lamNs, Number(e.target.value))} />
          <p className="hint">{customized ? 'Custom demand (overrides the scenario; the MDP policy is re-solved live).' : 'Move a slider to override the scenario demand.'}</p>
        </div>
        <div className="btn-row">
          <button className="primary" onClick={start}>{runStarted ? 'Restart' : 'Start'}</button>
          {state.status === 'running' && (state.paused
            ? <button onClick={sim.resume}>Resume</button>
            : <button onClick={sim.pause}>Pause</button>)}
          {state.status === 'running' && state.paused && <button onClick={sim.step}>Step</button>}
          {runStarted && <button onClick={sim.reset}>Reset</button>}
        </div>
        <p className="status" role="status">
          {state.status === 'idle' && 'Ready.'}
          {state.status === 'connecting' && 'Connecting…'}
          {state.status === 'running' && `${state.paused ? 'Paused' : 'Running'} — ${mm(state.t)} / ${mm(horizon)}`}
          {state.status === 'done' && `Finished (${mm(horizon)} simulated).`}
          {state.status === 'error' && <span className="err">{state.error}</span>}
        </p>
        {state.lam && <p className="hint">Current &lambda;: NS {state.lam[0].toFixed(2)}, EW {state.lam[1].toFixed(2)} veh/s</p>}
      </section>

      <section className="panels" aria-label="Intersections">
        {names.map(name => {
          const f = state.latest[name]
          const [lns, lew, p, e] = f?.state ?? [0, 0, 0, 0]
          return (
            <article className="card panel" key={name}>
              <h3 style={{ color: CONTROLLER_COLOR[name] }}>{CONTROLLER_LABEL[name]}</h3>
              <IntersectionCanvas frame={f} stepMs={stepMs} paused={state.paused}
                label={CONTROLLER_LABEL[name]} color={CONTROLLER_COLOR[name]} />
              {f ? (
                <dl className="hud">
                  <div><dt>MDP state</dt><dd>(q<sub>NS</sub>={LEVELS[lns]}, q<sub>EW</sub>={LEVELS[lew]}, {p === 0 ? 'NS' : 'EW'} green, e={e})</dd></div>
                  <div><dt>Green elapsed</dt><dd>{f.k * (state.config?.dt ?? 5)} s of max {state.config?.g_max ?? 60} s</dd></div>
                  <div><dt>Action</dt><dd>
                    {f.requested} {f.reason !== 'ok' && <>&rarr; <b>{f.applied}</b></>}{' '}
                    {f.reason === 'vetoed' && <span className="badge warn">VETOED &lt; G_min</span>}
                    {f.reason === 'forced' && <span className="badge bad">FORCED G_max</span>}
                    {f.reason === 'ok' && f.applied === 'SWITCH' && <span className="badge info">SWITCH</span>}
                  </dd></div>
                </dl>
              ) : <p className="hint">Press Start to run this controller.</p>}
            </article>
          )
        })}
      </section>

      {Object.keys(state.latest).length > 0 && (
        <section className="card" aria-label="Running metrics">
          <h3>Running metrics</h3>
          <div className="table-wrap">
            <table>
              <thead><tr>
                <th>Controller</th><th>Avg wait (s)</th><th>Mean queue</th><th>Max queue</th>
                <th>Throughput (veh/h)</th><th>Departed</th><th>Switches</th><th>Cum. reward</th>
              </tr></thead>
              <tbody>
                {Object.entries(state.latest).map(([name, f]) => (
                  <tr key={name}>
                    <th scope="row" style={{ color: CONTROLLER_COLOR[name] }}>{CONTROLLER_LABEL[name]}</th>
                    <td>{f.metrics.avg_wait_s.toFixed(1)}</td>
                    <td>{f.metrics.mean_queue.toFixed(1)}</td>
                    <td>{f.metrics.max_queue}</td>
                    <td>{f.metrics.throughput_vph.toFixed(0)}</td>
                    <td>{f.metrics.departed}</td>
                    <td>{f.metrics.switches}</td>
                    <td>{f.metrics.total_reward.toFixed(0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {Object.keys(state.series).length > 0 && (
        <section className="charts" aria-label="Live charts">
          <SeriesChart title="Total queue length" series={state.series} metric="queue" yLabel="vehicles waiting" />
          <SeriesChart title="Average waiting time so far" series={state.series} metric="wait" yLabel="seconds" />
        </section>
      )}
      {active && <span className="sr-only" aria-live="polite">Simulation running</span>}
    </div>
  )
}
