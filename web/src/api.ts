import type { ConfigJson, Metrics, PolicyPayload, ScenarioJson } from './types'

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const getConfig = () =>
  fetch('/api/config').then(r => j<{ config: ConfigJson; scenarios: ScenarioJson[] }>(r))

export interface SolveReq {
  scenario?: string
  lam_ns?: number
  lam_ew?: number
  gamma?: number
  c_switch?: number
  lanes?: number
}

export const solve = (req: SolveReq) =>
  fetch('/api/solve', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req),
  }).then(r => j<PolicyPayload>(r))

export interface SummaryRow {
  scenario: string
  controller: string
  runs: number
  [metric: string]: number | string
}

export interface BenchmarkPayload {
  summary: SummaryRow[]
  model_vs_sim: { scenario: string; weighted_tv: number; tv_queue_and_phase_only: number; tv_elapsed_only: number }[] | null
  qlearning: {
    agree_unweighted: number; agree_weighted: number; episodes: number
    avg_wait_by_policy?: Record<string, number>
  } | null
}

export const getBenchmark = () => fetch('/api/benchmark').then(r => j<BenchmarkPayload>(r))
export const runBenchmark = () =>
  fetch('/api/benchmark/run', { method: 'POST' }).then(r => j<{ summary: SummaryRow[] }>(r))

export type { Metrics }
