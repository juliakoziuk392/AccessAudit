export default function Kpis({ summary }) {
  const { accounts_total: total, accounts_flagged: flagged, findings, critical } = summary
  const pct = total ? Math.round((flagged / total) * 100) : 0
  const items = [
    { label: 'Перевірено акаунтів', value: total },
    { label: 'Акаунтів із проблемами', value: flagged, hint: `${pct}% від усіх` },
    { label: 'Усього знахідок', value: findings },
    { label: 'Критичних', value: critical, tone: critical ? 'crit' : '' },
  ]
  return (
    <section className="kpis">
      {items.map((k) => (
        <div className={`card kpi ${k.tone || ''}`} key={k.label}>
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value">{k.value}</div>
          {k.hint && <div className="muted small">{k.hint}</div>}
        </div>
      ))}
    </section>
  )
}
