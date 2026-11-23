import { useEffect, useRef } from 'react'
import type { CtrlFrame } from './types'

const W = 420
const H = 420
const CX = W / 2
const CY = H / 2
const ROAD = 76          // road width (both directions)
const LANE = ROAD / 2
const CAR_W = 13
const CAR_L = 10
const ROW = 12
const CAR_COLORS = ['#e5484d', '#3e63dd', '#f5a524', '#30a46c', '#8e4ec6', '#12a594', '#d6409f', '#6b7280']
const SIG_COLOR: Record<string, string> = { G: '#30a46c', Y: '#f5a524', R: '#e5484d' }
const NAMES = ['N', 'S', 'E', 'W']
const MAX_ROWS = 14
const CROSS_MS = 900

interface Crossing { i: number; d: number; c: string; lane: number }

/** Position of a car on approach i at distance d beyond the stop line (d < 0: inside/after it). */
function pos(i: number, d: number, lane: number): [number, number, boolean] {
  const off = (lane === 0 ? -1 : 1) * (LANE / 4)
  switch (i) {
    case 0: return [CX - LANE / 2 + off, CY - ROAD / 2 - d, true]    // from north, heading south
    case 1: return [CX + LANE / 2 + off, CY + ROAD / 2 + d, true]    // from south, heading north
    case 2: return [CX + ROAD / 2 + d, CY - LANE / 2 + off, false]   // from east, heading west
    default: return [CX - ROAD / 2 - d, CY + LANE / 2 + off, false]  // from west, heading east
  }
}

interface Props {
  frame?: CtrlFrame
  stepMs: number        // wall-clock duration of one decision step
  paused: boolean
  label: string
  color: string
}

export default function IntersectionCanvas({ frame, stepMs, paused, label, color }: Props) {
  const ref = useRef<HTMLCanvasElement>(null)
  const anim = useRef({
    frame: undefined as CtrlFrame | undefined, start: 0, shown: -1,
    q: [0, 0, 0, 0], sig: 'RR', cars: [] as Crossing[], last: 0, stepMs, paused,
  })

  anim.current.stepMs = stepMs
  anim.current.paused = paused

  // a new decision step arrived: restart the 5-tick playback
  useEffect(() => {
    const a = anim.current
    a.frame = frame
    a.start = performance.now()
    a.shown = -1
  }, [frame])

  useEffect(() => {
    const canvas = ref.current!
    const dpr = window.devicePixelRatio || 1
    canvas.width = W * dpr
    canvas.height = H * dpr
    const ctx = canvas.getContext('2d')!
    ctx.scale(dpr, dpr)
    let raf = 0

    const draw = (now: number) => {
      const a = anim.current
      const dtMs = a.last ? Math.min(100, now - a.last) : 16
      a.last = now
      const f = a.frame
      if (f) {
        const n = f.ticks.length
        const tickMs = Math.max(8, a.stepMs / n)
        const want = Math.min(n - 1, Math.floor((now - a.start) / tickMs))
        while (a.shown < want) {
          a.shown++
          const tk = f.ticks[a.shown]
          a.q = tk.q
          a.sig = tk.sig
          for (let i = 0; i < 4; i++) {
            for (let k = 0; k < tk.dep[i] && a.cars.length < 80; k++) {
              a.cars.push({ i, d: k * (CAR_L + 6), c: CAR_COLORS[(a.cars.length + i) % CAR_COLORS.length], lane: k % 2 })
            }
          }
        }
      }
      // move crossing cars
      const total = H / 2 + ROAD / 2
      const speed = total / CROSS_MS
      if (!a.paused) {
        for (const c of a.cars) c.d -= speed * dtMs
      }
      a.cars = a.cars.filter(c => c.d > -total)
      render(ctx, a)
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <canvas ref={ref} role="img" aria-label={`${label} intersection animation`}
      style={{ width: '100%', maxWidth: W, aspectRatio: '1 / 1', borderTop: `4px solid ${color}` }} />
  )
}

function css(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function car(ctx: CanvasRenderingContext2D, x: number, y: number, vertical: boolean, color: string) {
  ctx.fillStyle = color
  const w = vertical ? CAR_W : CAR_L
  const h = vertical ? CAR_L : CAR_W
  ctx.beginPath()
  ctx.roundRect(x - w / 2, y - h / 2, w, h, 2)
  ctx.fill()
}

function render(ctx: CanvasRenderingContext2D, a: { q: number[]; sig: string; cars: Crossing[] }) {
  ctx.clearRect(0, 0, W, H)
  ctx.fillStyle = css('--canvas-bg', '#e9ecef')
  ctx.fillRect(0, 0, W, H)
  // roads
  ctx.fillStyle = css('--road', '#3b4048')
  ctx.fillRect(CX - ROAD / 2, 0, ROAD, H)
  ctx.fillRect(0, CY - ROAD / 2, W, ROAD)
  // centre lines
  ctx.strokeStyle = 'rgba(255,255,255,.55)'
  ctx.setLineDash([10, 8])
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.moveTo(CX, 0); ctx.lineTo(CX, CY - ROAD / 2)
  ctx.moveTo(CX, CY + ROAD / 2); ctx.lineTo(CX, H)
  ctx.moveTo(0, CY); ctx.lineTo(CX - ROAD / 2, CY)
  ctx.moveTo(CX + ROAD / 2, CY); ctx.lineTo(W, CY)
  ctx.stroke()
  ctx.setLineDash([])

  // stop lines coloured by the signal of their axis
  const sigNS = SIG_COLOR[a.sig[0]] ?? '#e5484d'
  const sigEW = SIG_COLOR[a.sig[1]] ?? '#e5484d'
  ctx.lineWidth = 4
  const stop = (x1: number, y1: number, x2: number, y2: number, c: string) => {
    ctx.strokeStyle = c
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
  }
  stop(CX - LANE, CY - ROAD / 2, CX, CY - ROAD / 2, sigNS)   // N inbound (west half)
  stop(CX, CY + ROAD / 2, CX + LANE, CY + ROAD / 2, sigNS)   // S inbound (east half)
  stop(CX + ROAD / 2, CY - LANE, CX + ROAD / 2, CY, sigEW)   // E inbound (north half)
  stop(CX - ROAD / 2, CY, CX - ROAD / 2, CY + LANE, sigEW)   // W inbound (south half)

  // signal heads
  const head = (x: number, y: number, c: string) => {
    ctx.fillStyle = '#111'
    ctx.beginPath(); ctx.roundRect(x - 9, y - 9, 18, 18, 5); ctx.fill()
    ctx.fillStyle = c
    ctx.shadowColor = c; ctx.shadowBlur = 8
    ctx.beginPath(); ctx.arc(x, y, 5.5, 0, Math.PI * 2); ctx.fill()
    ctx.shadowBlur = 0
  }
  head(CX - ROAD / 2 - 16, CY - ROAD / 2 - 16, sigNS)
  head(CX + ROAD / 2 + 16, CY + ROAD / 2 + 16, sigNS)
  head(CX + ROAD / 2 + 16, CY - ROAD / 2 - 16, sigEW)
  head(CX - ROAD / 2 - 16, CY + ROAD / 2 + 16, sigEW)

  // queued cars (two columns per inbound lane)
  ctx.font = '600 11px system-ui, sans-serif'
  ctx.textBaseline = 'middle'
  for (let i = 0; i < 4; i++) {
    const q = a.q[i]
    const shown = Math.min(q, MAX_ROWS * 2)
    for (let k = 0; k < shown; k++) {
      const row = Math.floor(k / 2)
      const [x, y, vert] = pos(i, 7 + row * ROW, k % 2)
      car(ctx, x, y, vert, CAR_COLORS[(k + i * 3) % CAR_COLORS.length])
    }
    // queue count label near the end of the queue
    const labelD = 7 + Math.min(MAX_ROWS, Math.ceil(shown / 2) + 1) * ROW + 4
    const [lx, ly] = pos(i, labelD, 0)
    ctx.fillStyle = css('--text', '#111')
    ctx.textAlign = 'center'
    const txt = q > shown ? `${NAMES[i]} ${q} (+${q - shown})` : `${NAMES[i]} ${q}`
    const ox = i >= 2 ? (i === 2 ? 14 : -14) : 0
    ctx.fillText(txt, Math.max(30, Math.min(W - 30, lx + ox)), Math.max(10, Math.min(H - 10, ly)))
  }
  // cars crossing the junction
  for (const c of a.cars) {
    const [x, y, vert] = pos(c.i, c.d, c.lane)
    car(ctx, x, y, vert, c.c)
  }
}
