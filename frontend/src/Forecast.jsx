import { useEffect, useState } from 'react'
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const API = 'http://localhost:8000'
const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })

export default function Forecast({ categoryId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const q = categoryId ? `?category_id=${categoryId}` : ''
    fetch(`${API}/api/forecast${q}`)
      .then((r) => {
        if (!r.ok) throw new Error('failed')
        return r.json()
      })
      .then((d) => {
        setData(d)
        setError('')
      })
      .catch(() => setError('Could not load the forecast.'))
  }, [categoryId])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div>Loading forecast...</div>
  if (data.forecast.length === 0) {
    return <div className="panel">Not enough monthly history to forecast yet.</div>
  }

  const lastIndex = data.history.length - 1
  const rows = [
    ...data.history.map((h, i) => ({
      month: h.month,
      actual: h.revenue,
      // join the dashed lines to the last real month so the chart looks continuous
      forecast: i === lastIndex ? h.revenue : null,
      low: i === lastIndex ? h.revenue : null,
      high: i === lastIndex ? h.revenue : null,
    })),
    ...data.forecast.map((f) => ({
      month: f.month,
      forecast: f.revenue,
      low: f.low,
      high: f.high,
    })),
  ]

  const total = data.forecast.reduce((sum, f) => sum + f.revenue, 0)

  return (
    <>
      <h2 style={{ fontSize: 20, margin: '8px 0 12px' }}>Revenue forecast</h2>
      <div className="panel" style={{ marginBottom: 24 }}>
        <div className="cards" style={{ marginBottom: 16 }}>
          <div className="card">
            <div className="label">Expected revenue, next {data.forecast.length} months</div>
            <div className="value">{inr(total)}</div>
          </div>
          <div className="card">
            <div className="label">Trend per month</div>
            <div className="value">
              {data.trend_per_month >= 0 ? '+' : ''}
              {inr(data.trend_per_month)}
            </div>
          </div>
          <div className="card">
            <div className="label">Typical miss on past months</div>
            <div className="value">±{data.typical_error_pct}%</div>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
            <XAxis dataKey="month" fontSize={12} />
            <YAxis fontSize={12} tickFormatter={(v) => v / 1000 + 'k'} />
            <Tooltip formatter={(v) => inr(v)} />
            <Legend />
            <Line type="monotone" dataKey="actual" name="Actual" stroke="#2563eb" strokeWidth={2} />
            <Line type="monotone" dataKey="forecast" name="Forecast" stroke="#f97316"
                  strokeWidth={2} strokeDasharray="6 4" />
            <Line type="monotone" dataKey="low" name="Likely low" stroke="#fbbf24"
                  strokeWidth={1} strokeDasharray="2 3" dot={false} />
            <Line type="monotone" dataKey="high" name="Likely high" stroke="#fbbf24"
                  strokeWidth={1} strokeDasharray="2 3" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>

        <table style={{ marginTop: 16 }}>
          <thead>
            <tr><th>Month</th><th>Forecast</th><th>Likely range</th></tr>
          </thead>
          <tbody>
            {data.forecast.map((f) => (
              <tr key={f.month}>
                <td>{f.month}</td>
                <td>{inr(f.revenue)}</td>
                <td>{inr(f.low)} to {inr(f.high)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}