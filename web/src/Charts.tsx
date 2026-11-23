import {
  BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement,
  LogarithmicScale, PointElement, Tooltip,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'
import type { SeriesPoint } from './simReducer'
import { CONTROLLER_COLOR, CONTROLLER_LABEL } from './types'

ChartJS.register(CategoryScale, LinearScale, LogarithmicScale, PointElement, LineElement,
  BarElement, Tooltip, Legend)

const css = (n: string, d: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d
ChartJS.defaults.color = css('--text-dim', '#666')
ChartJS.defaults.font.family = 'system-ui, sans-serif'
const GRID = 'rgba(128,128,128,.18)'

export function SeriesChart({ title, series, metric, yLabel }: {
  title: string
  series: Record<string, SeriesPoint[]>
  metric: 'queue' | 'wait' | 'reward'
  yLabel: string
}) {
  const data = {
    datasets: Object.entries(series).map(([name, pts]) => ({
      label: CONTROLLER_LABEL[name] ?? name,
      data: pts.map(p => ({ x: p.t, y: p[metric] })),
      borderColor: CONTROLLER_COLOR[name] ?? '#888',
      backgroundColor: CONTROLLER_COLOR[name] ?? '#888',
      borderWidth: 2, pointRadius: 0, tension: 0.15,
    })),
  }
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <div className="chart-box">
        <Line data={data} options={{
          animation: false, parsing: false, maintainAspectRatio: false,
          interaction: { mode: 'nearest', intersect: false },
          scales: {
            x: { type: 'linear', title: { display: true, text: 'simulated time (s)' }, grid: { color: GRID } },
            y: { title: { display: true, text: yLabel }, grid: { color: GRID }, beginAtZero: metric !== 'reward' },
          },
          plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } },
        }} />
      </div>
    </figure>
  )
}

export function ConvergenceChart({ history }: { history: number[] }) {
  const data = {
    labels: history.map((_, i) => i + 1),
    datasets: [{
      label: 'max |Vₖ₊₁ − Vₖ|', data: history, borderColor: '#2f6fed',
      pointRadius: 0, borderWidth: 2,
    }],
  }
  return (
    <figure className="chart">
      <figcaption>Value Iteration convergence</figcaption>
      <div className="chart-box short">
        <Line data={data} options={{
          animation: false, maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: 'iteration' }, grid: { color: GRID } },
            y: { type: 'logarithmic', grid: { color: GRID } },
          },
          plugins: { legend: { display: false } },
        }} />
      </div>
    </figure>
  )
}

export function GroupedBars({ title, labels, datasets, yLabel }: {
  title: string
  labels: string[]
  datasets: { name: string; values: number[]; errors: number[] }[]
  yLabel: string
}) {
  const data = {
    labels,
    datasets: datasets.map(d => ({
      label: CONTROLLER_LABEL[d.name] ?? d.name, data: d.values,
      backgroundColor: CONTROLLER_COLOR[d.name] ?? '#888',
    })),
  }
  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      <div className="chart-box">
        <Bar data={data} options={{
          animation: false, maintainAspectRatio: false,
          scales: {
            x: { grid: { display: false } },
            y: { title: { display: true, text: yLabel }, grid: { color: GRID }, beginAtZero: true },
          },
          plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12 } },
            tooltip: {
              callbacks: {
                label: ctx => {
                  const d = datasets[ctx.datasetIndex]
                  const v = ctx.parsed.y ?? 0
                  return `${ctx.dataset.label}: ${v.toFixed(1)} ± ${d.errors[ctx.dataIndex].toFixed(1)}`
                },
              },
            },
          },
        }} />
      </div>
    </figure>
  )
}
