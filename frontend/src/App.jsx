import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import HistoryModal from './components/HistoryModal'

function statusClassByRatio(ratio) {
  if (ratio == null) return 'ok'
  if (ratio >= 0.9) return 'danger'
  if (ratio >= 0.6) return 'warn'
  return 'ok'
}

function clamp(n, min=0, max=1) { return Math.max(min, Math.min(max, n ?? 0)) }

function Card({ id, name, count, time, threshold, isAlert, onClick }) {
  const ratio = threshold ? clamp(count / threshold) : null
  const pct = ratio != null ? Math.round(ratio * 100) : null
  const angle = ratio != null ? Math.max(0, Math.min(360, ratio * 360)) : 0
  const ringClass = statusClassByRatio(ratio)
  return (
    <div className={`card${isAlert ? ' alert' : ''}`} onClick={onClick} style={{ cursor: 'pointer' }}>
      <div className={`ring ${ringClass}`} style={{ background: `conic-gradient(var(--ring-color, var(--success)) ${angle}deg, #eef2f7 0deg)` }}>
        <div className="ring-inner">{pct != null ? `${pct}%` : '—'}</div>
      </div>
      <div className="building">
        {name || 'Unknown'}
        {isAlert && <span className="badge">Threshold exceeded</span>}
      </div>
      <div className="count">Current Count: {count ?? '—'} {threshold != null && <span className="meta">/ {threshold}</span>}</div>
      <div className="meta">Last Updated: {time ?? 'N/A'}</div>
    </div>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [selected, setSelected] = useState(null) // { id, name }

  async function loadData() {
    try {
      const res = await fetch('/crowd', { cache: 'no-store' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setData(Array.isArray(json) ? json : [])
      setError(null)
      setLastRefresh(new Date())
    } catch (e) {
      setError(e)
    }
  }

  useEffect(() => {
    loadData()
    const id = setInterval(loadData, 10000) // 2 minutes to match DB update cadence
    return () => clearInterval(id)
  }, [])

  const refreshedText = useMemo(() => 
    lastRefresh ? `Updated ${lastRefresh.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Connecting…'
  , [lastRefresh])

  const kpis = useMemo(() => {
    const items = Array.isArray(data) ? data : []
    const totals = items.reduce((acc, it) => {
      if (typeof it.currentCount === 'number') acc.total += it.currentCount
      const hasTh = typeof it.threshold === 'number'
      if (hasTh) {
        acc.countWithTh += 1
        const r = it.threshold > 0 ? it.currentCount / it.threshold : 0
        acc.ratioSum += isFinite(r) ? r : 0
        if (it.currentCount > it.threshold) acc.alerts += 1
      }
      return acc
    }, { total: 0, alerts: 0, ratioSum: 0, countWithTh: 0 })
    const avgOcc = totals.countWithTh ? Math.round((totals.ratioSum / totals.countWithTh) * 100) : 0
    return {
      totalPeople: totals.total,
      alerts: totals.alerts,
      avgOccupancyPct: avgOcc,
    }
  }, [data])

  return (
    <div>
      <div className="header">
        <h1 className="title">Crowd Monitoring Dashboard</h1>
        <div className="subtle">{refreshedText} · Auto-refresh 10sec</div>
      </div>

      {/* KPI Row */}
      <div className="kpis">
        <div className="kpi">
          <div className="kpi-title">Total People Inside</div>
          <div className="kpi-value">{kpis.totalPeople}</div>
        </div>
        <div className="kpi">
          <div className="kpi-title">Buildings in Alert</div>
          <div className="kpi-value">{kpis.alerts}</div>
          <div className="kpi-sub">Current count above threshold</div>
        </div>
        <div className="kpi">
          <div className="kpi-title">Avg Occupancy</div>
          <div className="kpi-value">{kpis.avgOccupancyPct}%</div>
          <div className="kpi-sub">Avg of count/threshold</div>
        </div>
      </div>

      {error && <div className="error">Error: {String(error.message || error)}</div>}

      <div className="grid">
        {data === null && (
          <>
            <div className="skeleton" />
            <div className="skeleton" />
            <div className="skeleton" />
          </>
        )}

        {data?.length === 0 && <div className="info">No data available.</div>}

        {data?.map((item) => {
          const id = String(item.buildingId ?? item.buildingName ?? '')
          const threshold = typeof item.threshold === 'number' ? item.threshold : undefined
          const isAlert = typeof item.currentCount === 'number' && item.currentCount > threshold


          return (
            <Card
              key={id}
              id={id}
              name={item.buildingName}
              count={item.currentCount}
              time={item.timestamp}
              threshold={threshold}
              isAlert={isAlert}
              onClick={() => setSelected({ id, name: item.buildingName })}
            />
          )
        })}
      </div>

      <HistoryModal
        open={!!selected}
        building={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  )
}
