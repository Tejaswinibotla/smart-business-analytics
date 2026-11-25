import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import './App.css'

const API = 'http://localhost:8000'
const inr = (n) => '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })

function Card({ label, value }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  )
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const paths = ['kpis', 'revenue-trend', 'top-products', 'low-stock']
    Promise.all(
      paths.map((p) =>
        fetch(`${API}/api/${p}`).then((r) => {
          if (!r.ok) throw new Error(p)
          return r.json()
        })
      )
    )
      .then(([kpis, trend, top, stock]) => setData({ kpis, trend, top, stock }))
      .catch(() => setError('Could not load data. Is the API running on port 8000?'))
  }, [])

  if (error) return <div className="page"><div className="error">{error}</div></div>
  if (!data) return <div className="page">Loading...</div>

  const { kpis, trend, top, stock } = data

  return (
    <div className="page">
      <h1>Smart Business Dashboard</h1>
      <p className="sub">Sales, orders and inventory at a glance</p>

      <div className="cards">
        <Card label="Revenue (last 30 days)" value={inr(kpis.revenue)} />
        <Card label="Orders (last 30 days)" value={kpis.orders} />
        <Card label="Average order value" value={inr(kpis.avg_order_value)} />
      </div>

      <div className="grid2">
        <div className="panel">
          <h2>Monthly revenue</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
              <XAxis dataKey="month" fontSize={12} />
              <YAxis fontSize={12} tickFormatter={(v) => (v / 1000) + 'k'} />
              <Tooltip formatter={(v) => inr(v)} />
              <Line type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <h2>Top products by revenue</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={top} layout="vertical" margin={{ left: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f4" />
              <XAxis type="number" fontSize={12} tickFormatter={(v) => (v / 1000) + 'k'} />
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
            {stock.map((s) => (
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
    </div>
  )
}