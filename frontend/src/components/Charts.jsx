export const SEV = { Критично: 'crit', Середньо: 'mid', Низько: 'low' }
const LEVELS = ['Критично', 'Середньо', 'Низько']

// Горизонтальні стовпчики; кожен рядок — {label, parts: {критичність: кількість}}
function Bars({ rows }) {
  const max = Math.max(1, ...rows.map((r) => LEVELS.reduce((s, l) => s + (r.parts[l] || 0), 0)))
  return (
    <div className="bars">
      {rows.map((r) => {
        const total = LEVELS.reduce((s, l) => s + (r.parts[l] || 0), 0)
        return (
          <div className="bar-row" key={r.label}>
            <div className="bar-label" title={r.label}>
              {r.label}
            </div>
            <div className="bar-track">
              {LEVELS.map(
                (l) =>
                  r.parts[l] > 0 && (
                    <div
                      key={l}
                      className={`bar-seg ${SEV[l]}`}
                      style={{ width: `${(r.parts[l] / max) * 100}%` }}
                      title={`${l}: ${r.parts[l]}`}
                    />
                  ),
              )}
            </div>
            <div className="bar-total">{total}</div>
          </div>
        )
      })}
    </div>
  )
}

function pivot(items, key) {
  const map = new Map()
  for (const it of items) {
    if (!map.has(it[key])) map.set(it[key], {})
    map.get(it[key])[it.severity] = (map.get(it[key])[it.severity] || 0) + it.count
  }
  return [...map].map(([label, parts]) => ({ label, parts }))
}

export function Legend() {
  return (
    <div className="legend">
      {LEVELS.map((l) => (
        <span key={l}>
          <i className={`dot ${SEV[l]}`} /> {l}
        </span>
      ))}
    </div>
  )
}

export default function Charts({ summary }) {
  return (
    <section className="grid-2 charts">
      <div className="card">
        <h3>Знахідки за типом</h3>
        <Bars rows={pivot(summary.by_type, 'type')} />
        <Legend />
      </div>
      <div className="card">
        <h3>Знахідки за системою</h3>
        <Bars rows={pivot(summary.by_system, 'system')} />
        <Legend />
      </div>
    </section>
  )
}
