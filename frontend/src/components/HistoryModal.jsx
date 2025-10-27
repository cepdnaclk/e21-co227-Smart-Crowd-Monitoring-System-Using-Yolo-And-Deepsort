import { useEffect, useMemo, useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js'

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement, Tooltip, Legend)

export default function HistoryModal({ open, building, onClose }) {
  const [range, setRange] = useState(60) // minutes
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open || !building) return
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`/crowd/history?buildingId=${encodeURIComponent(building.id)}&minutes=${range}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        setData(Array.isArray(json) ? json : [])
      } catch (e) {
        setError(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [open, building?.id, range])

  const chartData = useMemo(() => {
    const labels = data?.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })) ?? []
    const series = data?.map(d => d.count ?? 0) ?? []
    return {
      labels,
      datasets: [
        {
          label: 'Crowd Count',
          data: series,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.15)',
          tension: 0.25,
          fill: true,
          pointRadius: 2,
        },
      ],
    }
  }, [data])

  const options = useMemo(() => ({
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false } },
      y: { beginAtZero: true, ticks: { precision: 0 } },
    },
  }), [])

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="title">{building?.name || 'Building'}</div>
            <div className="subtle">History (last {range} min)</div>
          </div>
          <button className="btn" onClick={onClose}>Close</button>
        </div>

        <div className="modal-toolbar">
          <label>Range:&nbsp;</label>
          <select value={range} onChange={(e) => setRange(Number(e.target.value))}>
            <option value={15}>15 min</option>
            <option value={60}>1 hour</option>
            <option value={180}>3 hours</option>
            <option value={360}>6 hours</option>
            <option value={1440}>24 hours</option>
          </select>
        </div>

        {loading && <div className="info" style={{ marginTop: 12 }}>Loading…</div>}
        {error && <div className="error" style={{ marginTop: 12 }}>Error: {String(error.message || error)}</div>}
        {!loading && !error && (
          <div style={{ height: 320 }}>
            <Line data={chartData} options={options} />
          </div>
        )}
      </div>
    </div>
  )
}
