import type { ConfigJson, Frame, InitMsg, Metrics, ScenarioJson, CtrlFrame } from './types'

export interface SeriesPoint { t: number; queue: number; wait: number; reward: number }

export interface SimState {
  status: 'idle' | 'connecting' | 'running' | 'done' | 'error'
  config: ConfigJson | null
  scenario: ScenarioJson | null
  controllers: string[]
  latest: Record<string, CtrlFrame>
  t: number
  lam: [number, number] | null
  series: Record<string, SeriesPoint[]>
  summary: Record<string, Metrics> | null
  error: string | null
  paused: boolean
}

export const initialSim: SimState = {
  status: 'idle', config: null, scenario: null, controllers: [], latest: {}, t: 0,
  lam: null, series: {}, summary: null, error: null, paused: false,
}

export type SimAction =
  | { type: 'connecting' }
  | InitMsg
  | { type: 'frames'; frames: Frame[] }
  | { type: 'done'; summary: Record<string, Metrics> }
  | { type: 'error'; message: string }
  | { type: 'paused'; value: boolean }
  | { type: 'reset' }

export function simReducer(state: SimState, action: SimAction): SimState {
  switch (action.type) {
    case 'reset':
      return initialSim
    case 'connecting':
      return { ...initialSim, status: 'connecting' }
    case 'init':
      return {
        ...initialSim, status: 'running', config: action.config, scenario: action.scenario,
        controllers: action.controllers,
        series: Object.fromEntries(action.controllers.map(c => [c, []])),
      }
    case 'frames': {
      if (action.frames.length === 0) return state
      const series = { ...state.series }
      for (const f of action.frames) {
        for (const [name, c] of Object.entries(f.controllers)) {
          const last = c.ticks[c.ticks.length - 1]
          const pt: SeriesPoint = {
            t: f.t,
            queue: last.q.reduce((a, b) => a + b, 0),
            wait: c.metrics.avg_wait_s,
            reward: c.metrics.total_reward,
          }
          series[name] = [...(series[name] ?? []), pt]
        }
      }
      const last = action.frames[action.frames.length - 1]
      return { ...state, latest: last.controllers, t: last.t, lam: last.lam, series }
    }
    case 'done':
      return { ...state, status: 'done', summary: action.summary }
    case 'error':
      return { ...state, status: 'error', error: action.message }
    case 'paused':
      return { ...state, paused: action.value }
    default:
      return state
  }
}
