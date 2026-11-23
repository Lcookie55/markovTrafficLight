import { useCallback, useEffect, useMemo, useState } from 'react'
import { getBenchmark, runBenchmark } from './api'
import type { BenchmarkPayload, SummaryRow } from './api'
import { GroupedBars } from './Charts'
import { CONTROLLER_COLOR, CONTROLLER_LABEL } from './types'

const METRICS: { key: string; label: string; unit: string; lowerBetter: boolean }[] = [
  { key: 'avg_wait_s', label: 'Average waiting time', unit: 's', lowerBetter: true },
  { key: 'mean_queue', label: 'Mean total queue', unit: 'veh', lowerBetter: true },
  { key: 'max_queue', label: 'Max total queue', unit: 'veh', lowerBetter: true },
  { key: 'throughput_vph', label: 'Throughput', unit: 'veh/h', lowerBetter: false },
  { key: 'switches', label: 'Phase switches', unit: '', lowerBetter: true },
]
const ORDER = ['fixed', 'lqf', 'mdp_nominal', 'mdp']

function toCsv(rows: SummaryRow[]): string {
  if (!rows.length) return ''
  const cols = Object.keys(rows[0])
  return [cols.join(','), ...rows.map(r => cols.map(c => r[c]).join(','))].join('\n')
}

export default function BenchmarkView() {
  const [data, setData] = useState<BenchmarkPayload | null>(null)
  const [metric, setMetric] = useState('avg_wait_s')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(() => {
    getBenchmark().then(setData).catch(e => setErr(String(e.message ?? e)))
  }, [])
  useEffect(load, [load])

  const rerun = () => {
    setBusy(true); setErr(null)
    runBenchmark().then(() => getBenchmark()).then(setData)
      .catch(e => setErr(String(e.message ?? e))).finally(() => setBusy(false))
  }

  const m = METRICS.find(x => x.key === metric)!
  const scenarios = useMemo(() => [...new Set((data?.summary ?? []).map(r => r.scenario))], [data])
  const controllers = useMemo(() => ORDER.filter(c => (data?.summary ?? []).some(r => r.controller === c)), [data])

  const get = (sid: string, c: string, suffix: 'mean' | 'std') => {
    const row = data?.summary.find(r => r.scenario === sid && r.controller === c)
    return row ? Number(row[`${metric}_${suffix}`] ?? 0) : 0
  }

  const best = (sid: string) => {
    const vals = controllers.map(c => [c, get(sid, c, 'mean')] as const)
    return vals.reduce((a, b) => (m.lowerBetter ? (b[1] < a[1] ? b : a) : (b[1] > a[1] ? b : a)))[0]
  }

  const download = () => {
    const blob = new Blob([toCsv(data?.summary ?? [])], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob); a.download = 'summary.csv'; a.click()
    URL.revokeObjectURL(a.href)
  }

  if (err && !data) return <p className="err" role="alert">{err}</p>
  if (!data) return <p className="hint">Loading&hellip;</p>
  if (!data.summary.length) {
    return (
      <section className="card">
        <p>No results yet. Run the experiment grid (5 scenarios &times; 5 seeds &times; 4 controllers, a few seconds).</p>
        <button className="primary" onClick={rerun} disabled={busy}>{busy ? 'Running…' : 'Run benchmark'}</button>
      </section>
    )
  }

  return (
    <div className="benchmark">
      <section className="card controls row">
        <div className="field">
          <label htmlFor="met">Metric</label>
          <select id="met" value={metric} onChange={e => setMetric(e.target.value)}>
            {METRICS.map(x => <option key={x.key} value={x.key}>{x.label}{x.unit && ` (${x.unit})`}</option>)}
          </select>
        </div>
        <div className="btn-row">
          <button onClick={rerun} disabled={busy}>{busy ? 'Running…' : 'Re-run benchmark'}</button>
          <button onClick={download}>Download CSV</button>
        </div>
        {err && <p className="err" role="alert">{err}</p>}
      </section>

      <GroupedBars title={`${m.label} by scenario (mean ± std over seeds)`}
        labels={scenarios}
        yLabel={m.unit}
        datasets={controllers.map(c => ({
          name: c,
          values: scenarios.map(s => get(s, c, 'mean')),
          errors: scenarios.map(s => get(s, c, 'std')),
        }))} />

      <section className="card">
        <h3>{m.label}{m.unit && ` (${m.unit})`} &mdash; {m.lowerBetter ? 'lower is better' : 'higher is better'}</h3>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Scenario</th>{controllers.map(c => (
              <th key={c} style={{ color: CONTROLLER_COLOR[c] }}>{CONTROLLER_LABEL[c]}</th>))}</tr></thead>
            <tbody>
              {scenarios.map(s => (
                <tr key={s}>
                  <th scope="row">{s}</th>
                  {controllers.map(c => (
                    <td key={c} className={best(s) === c ? 'best' : ''}>
                      {get(s, c, 'mean').toFixed(1)} <span className="dim">&plusmn; {get(s, c, 'std').toFixed(1)}</span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="hint">Every controller faces identical arrival streams (same seeds). Avg wait includes vehicles still queued at the end of the hour. Best value per row is highlighted.</p>
      </section>

      {(data.model_vs_sim || data.qlearning) && (
        <section className="card">
          <h3>Model checks</h3>
          {data.model_vs_sim && (
            <>
              <p>Total-variation distance between the analytic P(s&prime;|s,a) and transitions observed in the simulator
                (0 = identical, 1 = disjoint), weighted by visits:</p>
              <div className="table-wrap"><table>
                <thead><tr><th>Scenario</th><th>Overall TV</th><th>Queue + phase part</th><th>Elapsed part</th></tr></thead>
                <tbody>{data.model_vs_sim.map(r => (
                  <tr key={r.scenario}><th scope="row">{r.scenario}</th><td>{r.weighted_tv.toFixed(3)}</td>
                    <td>{r.tv_queue_and_phase_only.toFixed(3)}</td><td>{r.tv_elapsed_only.toFixed(3)}</td></tr>))}</tbody>
              </table></div>
            </>
          )}
          {data.qlearning && (
            <p>Q-Learning ({data.qlearning.episodes} episodes on the simulator) agrees with the Value-Iteration policy on{' '}
              <b>{(data.qlearning.agree_unweighted * 100).toFixed(0)}%</b> of the 32 free decisions
              ({(data.qlearning.agree_weighted * 100).toFixed(0)}% weighted by visits).</p>
          )}
        </section>
      )}
    </div>
  )
}
