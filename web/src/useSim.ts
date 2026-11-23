import { useCallback, useEffect, useReducer, useRef } from 'react'
import { initialSim, simReducer } from './simReducer'
import type { Frame } from './types'

export interface StartReq {
  scenario: string
  seed: number
  controllers: string[]
  speed: number
  lam_ns?: number
  lam_ew?: number
}

/** Owns the WebSocket. Frames are buffered and flushed once per animation frame. */
export function useSim() {
  const [state, dispatch] = useReducer(simReducer, initialSim)
  const wsRef = useRef<WebSocket | null>(null)
  const bufRef = useRef<Frame[]>([])
  const rafRef = useRef<number | null>(null)

  const flush = useCallback(() => {
    rafRef.current = null
    if (bufRef.current.length) {
      const frames = bufRef.current
      bufRef.current = []
      dispatch({ type: 'frames', frames })
    }
  }, [])

  const close = useCallback(() => {
    const ws = wsRef.current
    wsRef.current = null
    if (ws) { ws.onmessage = null; ws.onclose = null; ws.onerror = null; ws.close() }
    bufRef.current = []
  }, [])

  const start = useCallback((req: StartReq) => {
    close()
    dispatch({ type: 'connecting' })
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/sim`)
    wsRef.current = ws
    ws.onopen = () => ws.send(JSON.stringify({ type: 'start', ...req }))
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data)
      if (m.type === 'frame') {
        bufRef.current.push(m as Frame)
        if (rafRef.current == null) rafRef.current = requestAnimationFrame(flush)
      } else if (m.type === 'init') {
        dispatch(m)
      } else if (m.type === 'done') {
        flush()
        dispatch(m)
      } else if (m.type === 'error') {
        dispatch({ type: 'error', message: m.message })
      }
    }
    ws.onerror = () => dispatch({ type: 'error', message: 'Cannot reach the API. Is `uvicorn api.main:app` running on :8000?' })
  }, [close, flush])

  const send = useCallback((msg: object) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg))
  }, [])

  const pause = useCallback(() => { send({ type: 'pause' }); dispatch({ type: 'paused', value: true }) }, [send])
  const resume = useCallback(() => { send({ type: 'resume' }); dispatch({ type: 'paused', value: false }) }, [send])
  const step = useCallback(() => send({ type: 'step' }), [send])
  const setSpeed = useCallback((value: number) => send({ type: 'speed', value }), [send])
  const setLambda = useCallback((lam_ns: number, lam_ew: number) => send({ type: 'set_lambda', lam_ns, lam_ew }), [send])
  const reset = useCallback(() => { close(); dispatch({ type: 'reset' }) }, [close])

  useEffect(() => () => { close(); if (rafRef.current) cancelAnimationFrame(rafRef.current) }, [close])

  return { state, start, pause, resume, step, setSpeed, setLambda, reset }
}
