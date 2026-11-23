export interface Tick { sig: string; q: number[]; dep: number[]; arr: number[] }

export interface Metrics {
  avg_wait_s: number
  avg_wait_departed_s: number
  mean_queue: number
  max_queue: number
  max_queue_approach: number
  throughput_vph: number
  arrived: number
  departed: number
  remaining: number
  switches: number
  forced_switches: number
  vetoed_switches: number
  total_reward: number
}

export type Reason = 'ok' | 'vetoed' | 'forced'

export interface CtrlFrame {
  state: [number, number, number, number]
  state_idx: number
  k: number
  requested: 'KEEP' | 'SWITCH'
  applied: 'KEEP' | 'SWITCH'
  reason: Reason
  reward: number
  ticks: Tick[]
  metrics: Metrics
}

export interface Frame {
  type: 'frame'
  t: number
  lam: [number, number]
  controllers: Record<string, CtrlFrame>
}

export interface ConfigJson {
  dt: number; g_min: number; g_max: number; t_yellow: number; t_allred: number
  mu: number; lanes: number; gamma: number; c_switch: number; q_max: number
  eps: number; horizon: number; fixed_green: number; nominal_lambda: number
  seeds: number[]
}

export interface ScenarioJson {
  id: string; name: string; description: string
  lam_ns: number; lam_ew: number; surge: [number, number, number] | null
}

export interface InitMsg {
  type: 'init'
  config: ConfigJson
  scenario: ScenarioJson
  controllers: string[]
  seed: number
}

export interface PolicyState {
  idx: number; q_ns: number; q_ew: number; phase: number; e: number
  action: 'KEEP' | 'SWITCH'; kind: 'free' | 'vetoed' | 'forced'
  q_keep: number; q_switch: number; v: number
}

export interface PolicyPayload {
  label: string; lam_ns: number; lam_ew: number
  params: ConfigJson
  states: PolicyState[]
  iterations: number; history: number[]
  pi_iterations: number; vi_equals_pi: boolean
}

export const CONTROLLER_LABEL: Record<string, string> = {
  mdp: 'MDP (solved for scenario)',
  mdp_nominal: 'MDP (nominal demand)',
  fixed: 'Fixed-time 30 s / 30 s',
  lqf: 'Longest-queue-first',
}

export const CONTROLLER_COLOR: Record<string, string> = {
  mdp: '#2f6fed',
  mdp_nominal: '#13a8a8',
  fixed: '#e07b00',
  lqf: '#9b51e0',
}
