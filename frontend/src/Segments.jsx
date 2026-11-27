import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const API = 'http://localhost:8000'
const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })

const COLORS = {
  Champions: '#16a34a',
  Loyal: '#2563eb',
  Promising: '#06b6d4',
  'Needs attention': '#f59e0b',
  'At risk': '#ef4444',
  Hibernating: '#9ca3af',
}

const MEANING = {
  Champions: 'Recent, frequent, highest spend',
  Loyal: 'Regular buyers with good spend',
  Promising: 'Bought recently, spend still low',
  'Needs attention': 'Average, starting to cool off',
  'At risk': 'Good spenders who went quiet',
  Hibernating: 'Low spend and not seen for a while',
}

export default function Segments() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API}/api/customer-segments`)
      .then((r) => {
        if (!r.ok) throw new Error('failed')
        return r.json()
      })
      .then(setData)
      .catch(() => setError('Could not load customer segments.'))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div>Loading customer segments...</div>

  return (
    <>
      <h2 style={{ fontSize: 20, margin: '8px 0 12px' }}>Customer segments (RFM)</h2>

      <div className="grid2">
        <div className="panel">
          <h2>Customers by segment</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.segments} layout="vertical" margin={{ left: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
              <XAxis type="number" fontSize={12} />
              <YAxis type="category" dataKey="segment" fontSize={12} width={110} />
              <Tooltip />
              <Bar dataKey="customers">
                {data.segments.map((s) => (
                  <Cell key={s.segment} fill={COLORS[s.segment]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h2>Segment summary</h2>
          <table>
            <thead>
              <tr><th>Segment</th><th>Customers</th><th>Revenue</th><th>Days since order</th></tr>
            </thead>
            <tbody>
              {data.segments.map((s) => (
                <tr key={s.segment}>
                  <td>
                    <strong>{s.segment}</strong>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>{MEANING[s.segment]}</div>
                  </td>
                  <td>{s.customers}</td>
                  <td>{inr(s.revenue)}</td>
                  <td>{s.avg_recency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 24 }}>
        <h2>At-risk customers worth winning back</h2>
        <table>
          <thead>
            <tr><th>Customer</th><th>City</th><th>Days since last order</th><th>Orders</th><th>Total spent</th></tr>
          </thead>
          <tbody>
            {data.at_risk.map((c) => (
              <tr key={c.name}>
                <td>{c.name}</td>
                <td>{c.city}</td>
                <td>{c.recency}</td>
                <td>{c.frequency}</td>
                <td>{inr(c.monetary)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}