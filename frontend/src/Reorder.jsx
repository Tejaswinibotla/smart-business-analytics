import { useEffect, useState } from 'react'

const API = 'http://localhost:8000'
const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })

const STATUS_STYLE = {
  'Order now': { background: '#ffe4e6', color: '#be123c' },
  'Order soon': { background: '#fef3c7', color: '#92400e' },
  Healthy: { background: '#dcfce7', color: '#166534' },
  'No recent sales': { background: '#f3f4f6', color: '#4b5563' },
}

const daysText = (d) => (d === null ? '—' : d > 365 ? '365+' : d)

export default function Reorder({ categoryId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const q = categoryId ? `?category_id=${categoryId}` : ''
    fetch(`${API}/api/reorder${q}`)
      .then((r) => {
        if (!r.ok) throw new Error('failed')
        return r.json()
      })
      .then((d) => {
        setData(d)
        setError('')
      })
      .catch(() => setError('Could not load reorder suggestions.'))
  }, [categoryId])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div>Loading reorder suggestions...</div>

  return (
    <>
      <h2 style={{ fontSize: 20, margin: '8px 0 12px' }}>Reorder suggestions</h2>
      <div className="panel" style={{ marginBottom: 24 }}>
        <div className="cards" style={{ marginBottom: 16 }}>
          <div className="card">
            <div className="label">Order now</div>
            <div className="value">{data.order_now}</div>
          </div>
          <div className="card">
            <div className="label">Order soon</div>
            <div className="value">{data.order_soon}</div>
          </div>
          <div className="card">
            <div className="label">Estimated spend on suggested orders</div>
            <div className="value">{inr(data.total_cost)}</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Product</th><th>Supplier</th><th>In stock</th><th>Sold / day</th>
              <th>Days left</th><th>Status</th><th>Order qty</th><th>Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((i) => (
              <tr key={i.sku}>
                <td>
                  <strong>{i.name}</strong>
                  <div style={{ fontSize: 12, color: '#8a6f5d' }}>{i.sku}</div>
                </td>
                <td>{i.supplier || '—'}</td>
                <td>{i.stock}</td>
                <td>{i.daily_sales}</td>
                <td>{daysText(i.days_left)}</td>
                <td>
                  <span className="badge" style={STATUS_STYLE[i.status]}>{i.status}</span>
                </td>
                <td>{i.suggested_qty || '—'}</td>
                <td>{i.est_cost ? inr(i.est_cost) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p style={{ fontSize: 12, color: '#8a6f5d', margin: '12px 0 0' }}>
          Based on sales of the last 30 days. Assumes a {data.lead_time_days}-day supplier delivery
          time, and each suggested order covers {data.cover_days} days of sales.
        </p>
      </div>
    </>
  )
}