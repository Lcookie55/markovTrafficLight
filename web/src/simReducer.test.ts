import { describe, expect, it } from 'vitest'
import { initialSim, simReducer } from './simReducer'
import type { CtrlFrame, Frame, Metrics } from './types'

const metrics: Metrics = {
  avg_wait_s: 4, avg_wait_departed_s: 3, mean_queue: 2, max_queue: 5, max_queue_approach: 3,
  throughput_vph: 100, arrived: 10, departed: 8, remaining: 2, switches: 1,
  forced_switches: 0, vetoed_switches: 0, total_reward: -12,
}

function ctrl(q: number[]): CtrlFrame {
  return {
    state: [1, 0, 0, 1], state_idx: 7, k: 3, requested: 'KEEP', applied: 'KEEP', reason: 'ok',
    reward: -3, metrics,
    ticks: [{ sig: 'GR', q, dep: [0, 0, 0, 0], arr: [0, 0, 0, 0] }],
  }
}

function frame(t: number, q: number[]): Frame {
  return { type: 'frame', t, lam: [0.1, 0.1], controllers: { mdp: ctrl(q), fixed: ctrl(q) } }
}

describe('simReducer', () => {
  it('starts a run and accumulates one series point per frame and controller', () => {
    let s = simReducer(initialSim, { type: 'connecting' })
    expect(s.status).toBe('connecting')
    s = simReducer(s, {
      type: 'init', config: {} as never, scenario: {} as never, controllers: ['mdp', 'fixed'], seed: 1,
    })
    expect(s.status).toBe('running')
    s = simReducer(s, { type: 'frames', frames: [frame(5, [1, 2, 0, 1]), frame(10, [2, 2, 0, 1])] })
    expect(s.t).toBe(10)
    expect(s.series.mdp.map(p => p.queue)).toEqual([4, 5])
    expect(s.series.fixed).toHaveLength(2)
    expect(s.latest.mdp.state_idx).toBe(7)
  })

  it('ignores an empty batch and records the final summary', () => {
    const s0 = simReducer(initialSim, { type: 'reset' })
    expect(simReducer(s0, { type: 'frames', frames: [] })).toBe(s0)
    const s1 = simReducer(s0, { type: 'done', summary: { mdp: metrics } })
    expect(s1.status).toBe('done')
    expect(s1.summary?.mdp.avg_wait_s).toBe(4)
  })
})
