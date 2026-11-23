import { useEffect, useRef, useState } from 'react'
import { solve } from './api'
import { ConvergenceChart } from './Charts'
import type { PolicyPayload, PolicyState, ScenarioJson } from './types'

const LEVELS = ['0', '1–3', '4–7', '8+']
const E_LABEL = ['e = 0 (< G_min): switch vetoed', 'e = 1 (G_min ≤ t < G_max): free decision', 'e = 2 (≥ G_max): switch forced']

function Grid({ states, phase, e, current }: {
  states: PolicyState[]; phase: number; e: number; current: number | null
}) {
  const cell = (ns: number, ew: number) =>
    states.find(s => s.q_ns === ns && s.q_ew === ew && s.phase === phase && s.e === e)!
  return (
    <div className="grid-wrap">
      <div className="grid-title">{phase === 0 ? 'North–South green' : 'East–West green'} &middot; {E_LABEL[e]}</div>
      <table className="policy-grid">
        <thead>
          <tr><th className="corner">q<sub>NS</sub> \ q<sub>EW</sub></th>{LEVELS.map(l => <th key={l} scope="col">{l}</th>)}</tr>
        </thead>
        <tbody>
          {[0, 1, 2, 3].map(ns => (
            <tr key={ns}>
              <th scope="row">{LEVELS[ns]}</th>
              {[0, 1, 2, 3].map(ew => {
                const c = cell(ns, ew)
                const sw = c.action === 'SWITCH'
                return (
                  <td key={ew}
                    className={`${sw ? 'sw' : 'kp'} ${c.kind} ${current === c.idx ? 'current' : ''}`}
                    title={`${c.action}${c.kind !== 'free' ? ` (${c.kind})` : ''}\nQ(keep)=${c.q_keep.toFixed(1)}  Q(switch)=${c.q_switch.toFixed(1)}\nV*=${c.v.toFixed(1)}`}>
                    <span>{sw ? 'SWITCH' : 'KEEP'}</span>
                    <small>{c.v.toFixed(0)}</small>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function PolicyView({ scenarios, currentState }: {
  scenarios: ScenarioJson[]; currentState: number | null
}) {
  const [scenario, setScenario] = useState('S3')
  const [gamma, setGamma] = useState(0.95)
  const [cSwitch, setCSwitch] = useState(2)
  const [data, setData] = useState<PolicyPayload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const seq = useRef(0)

  useEffect(() => {
    const id = ++seq.current
    setBusy(true)
    const t = window.setTimeout(() => {
      solve({ scenario, gamma, c_switch: cSwitch })
        .then(d => { if (id === seq.current) { setData(d); setErr(null) } })
        .catch(e => { if (id === seq.current) setErr(String(e.message ?? e)) })
        .finally(() => { if (id === seq.current) setBusy(false) })
    }, 120)
    return () => window.clearTimeout(t)
  }, [scenario, gamma, cSwitch])

  const nSwitch = data ? data.states.filter(s => s.kind === 'free' && s.action === 'SWITCH').length : 0

  return (
    <div className="policy">
      <section className="card controls">
        <div className="field">
          <label htmlFor="pscn">Demand used to build P(s&prime;|s,a)</label>
          <select id="pscn" value={scenario} onChange={e => setScenario(e.target.value)}>
            {scenarios.map(s => <option key={s.id} value={s.id}>{s.id} – {s.name}</option>)}
            <option value="nominal">Nominal (0.20 / 0.20)</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="g">Discount factor &gamma; = {gamma.toFixed(2)}</label>
          <input id="g" type="range" min={0.5} max={0.99} step={0.01} value={gamma} onChange={e => setGamma(Number(e.target.value))} />
        </div>
        <div className="field">
          <label htmlFor="cs">Switching cost c<sub>switch</sub> = {cSwitch.toFixed(1)}</label>
          <input id="cs" type="range" min={0} max={10} step={0.5} value={cSwitch} onChange={e => setCSwitch(Number(e.target.value))} />
        </div>
        {data && (
          <ul className="facts">
            <li>Value Iteration: <b>{data.iterations}</b> iterations (&epsilon; = 1e-4)</li>
            <li>Policy Iteration: <b>{data.pi_iterations}</b> iterations &mdash; {data.vi_equals_pi
              ? <span className="badge ok">same policy as VI</span> : <span className="badge bad">policies differ</span>}</li>
            <li>Free decisions that SWITCH: <b>{nSwitch}</b> of 32</li>
            <li>&lambda; used: NS {data.lam_ns.toFixed(3)}, EW {data.lam_ew.toFixed(3)} veh/s</li>
          </ul>
        )}
        {busy && <p className="hint" role="status">Solving&hellip;</p>}
        {err && <p className="err" role="alert">{err}</p>}
        <p className="hint">Blue = KEEP, orange = SWITCH. Hatched cells are decided by the safety layer, not by the policy. The small number is V*(s). The outlined cell is the live state of the MDP controller while a simulation runs.</p>
      </section>
      <section className="grids" aria-label="Optimal policy">
        {data && [1, 0, 2].map(e => (
          <div className="grid-row" key={e}>
            {[0, 1].map(p => <Grid key={p} states={data.states} phase={p} e={e} current={currentState} />)}
          </div>
        ))}
        {data && <ConvergenceChart history={data.history} />}
      </section>
    </div>
  )
}
