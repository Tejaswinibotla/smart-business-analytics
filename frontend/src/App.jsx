import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import './App.css'

const API = 'http://localhost:8000'
const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
const iso = (d) => d.toISOString().slice(0, 10)
const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return iso(d)
}

function Card({ label, value }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  )
}

export default function App() {
  const [start, setStart] = useState(daysAgo(30))
  const [end, setEnd] = useState(iso(new Date()))
  const [categoryId, setCategoryId] = useState('')
  const [categories, setCategories] = useState([])
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const preset = (days) => {
    setStart(daysAgo(days))
    setEnd(iso(new Date()))
  }

  useEffect(() => {
    fetch(`${API}/api/categories`)
      .then((r) => r.json())
      .then(setCategories)
      .catch(() => {})
  }, [])

  useEffect(() => {
    const qs = new URLSearchParams()
    if (start) qs.set('start', start)
    if (end) qs.set('end', end)
    if (categoryId) qs.set('category_id', categoryId)
    const q = qs.toString() ? `?${qs}` : ''

    Promise.all(
      ['kpis', 'revenue-trend', 'top-products', 'low-stock'].map((p) =>
        fetch(`${API}/api/${p}${q}`).then((r) => {
          if (!r.ok) throw new Error(p)
          return r.json()
        })
      )
    )
      .then(([kpis, trend, top, stock]) => {
        setData({ kpis, trend, top, stock })
        setError('')
      })
      .catch(() => setError('Could not load data. Is the API running on port 8000?'))
  }, [start, end, categoryId])

  return (
    <div className="page">
      <h1>Smart Business Dashboard</h1>
      <p className="sub">Sales, orders and inventory at a glance</p>

      <div className="filters">
        <label>
          From
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label>
          Category
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <div className="presets">
          <button onClick={() => preset(30)}>30 days</button>
          <button onClick={() => preset(90)}>90 days</button>
          <button onClick={() => preset(365)}>12 months</button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {!data && !error && <div>Loading...</div>}

      {data && (
        <>
          <div className="cards">
            <Card label="Revenue" value={inr(data.kpis.revenue)} />
            <Card label="Orders" value={data.kpis.orders} />
            <Card label="Average order value" value={inr(data.kpis.avg_order_value)} />
          </div>

          <div className="grid2">
            <div className="panel">
              <h2>Monthly revenue</h2>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={data.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                  <XAxis dataKey="month" fontSize={12} />
                  <YAxis fontSize={12} tickFormatter={(v) => v / 1000 + 'k'} />
                  <Tooltip formatter={(v) => inr(v)} />
                  <Line type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="panel">
              <h2>Top products by revenue</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.top} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
                  <XAxis type="number" fontSize={12} tickFormatter={(v) => v / 1000 + 'k'} />
                  <YAxis type="category" dataKey="name" fontSize={11} width={110} />
                  <Tooltip formatter={(v) => inr(v)} />
                  <Bar dataKey="revenue" fill="#16a34a" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="panel">
            <h2>Lowest stock</h2>
            <table>
              <thead>
                <tr><th>SKU</th><th>Product</th><th>In stock</th><th>Reorder level</th><th>Status</th></tr>
              </thead>
              <tbody>
                {data.stock.map((s) => (
                  <tr key={s.sku}>
                    <td>{s.sku}</td>
                    <td>{s.name}</td>
                    <td>{s.stock}</td>
                    <td>{s.reorder_level}</td>
                    <td>
                      <span className={'badge ' + (s.stock <= s.reorder_level ? 'low' : 'ok')}>
                        {s.stock <= s.reorder_level ? 'Reorder' : 'OK'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}