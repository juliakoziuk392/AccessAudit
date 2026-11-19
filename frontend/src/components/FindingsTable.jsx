import { useMemo, useRef, useState } from 'react'
import { downloadCsv } from '../api.js'
import { SEV } from './Charts.jsx'

const LEVELS = ['Критично', 'Середньо', 'Низько']
const PAGE_SIZE = 50

export default function FindingsTable({ rows, onExcel }) {
  const [levels, setLevels] = useState(LEVELS)
  const [system, setSystem] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const top = useRef(null)

  const systems = useMemo(() => [...new Set(rows.map((r) => r.system))].sort(), [rows])
  const shown = useMemo(() => {
    const s = q.trim().toLowerCase()
    return rows.filter(
      (r) =>
        levels.includes(r.severity) &&
        (!system || r.system === system) &&
        (!s || [r.login, r.employee, r.email].some((v) => v && String(v).toLowerCase().includes(s))),
    )
  }, [rows, levels, system, q])

  const accountsCount = useMemo(() => new Set(shown.map((r) => `${r.system}\u0000${r.login}`)).size, [shown])

  const pages = Math.max(1, Math.ceil(shown.length / PAGE_SIZE))
  const current = Math.min(page, pages)
  const from = (current - 1) * PAGE_SIZE

  const goTo = (p) => {
    setPage(p)
    top.current?.scrollIntoView({ block: 'start' })
  }

  const toggle = (l) => {
    setPage(1)
    setLevels((cur) => (cur.includes(l) ? cur.filter((x) => x !== l) : [...cur, l]))
  }

  return (
    <section className="card" ref={top}>
      <div className="section-head">
        <h3>
          Усі знахідки <span className="muted">({shown.length})</span>
          <span className="muted accounts-count"> · акаунтів до перевірки: {accountsCount}</span>
        </h3>
        <div className="row">
          <button className="btn small primary" onClick={() => onExcel(shown)}>
            ⬇ Excel{shown.length !== rows.length ? ' (за фільтром)' : ''}
          </button>
          <button className="btn small" onClick={() => downloadCsv(shown, 'access_review_report.csv')}>
            ⬇ CSV
          </button>
        </div>
      </div>

      <div className="filters">
        <div className="pills">
          {LEVELS.map((l) => (
            <button key={l} className={`pill ${SEV[l]} ${levels.includes(l) ? 'on' : ''}`} onClick={() => toggle(l)}>
              <i className={`dot ${SEV[l]}`} /> {l}
            </button>
          ))}
        </div>
        <select value={system} onChange={(e) => { setSystem(e.target.value); setPage(1) }}>
          <option value="">Усі системи</option>
          {systems.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <input
          type="search"
          placeholder="Пошук за логіном, ім’ям, поштою…"
          value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1) }}
        />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Критичність</th>
              <th>Система</th>
              <th>Логін</th>
              <th>Роль</th>
              <th>Проблема</th>
            </tr>
          </thead>
          <tbody>
            {shown.slice(from, from + PAGE_SIZE).map((r, i) => (
              <tr key={from + i}>
                <td>
                  <span className={`sev ${SEV[r.severity]}`}>{r.severity}</span>
                </td>
                <td>{r.system}</td>
                <td>
                  <strong>{r.login}</strong>
                  {r.employee && <div className="muted small">{r.employee}</div>}
                </td>
                <td>
                  <code>{r.role}</code>
                </td>
                <td>{r.issue}</td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan="5" className="muted center-text">
                  Нічого не знайдено за цими фільтрами
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {shown.length > PAGE_SIZE && (
        <div className="pager">
          <span className="muted small">
            {from + 1}–{Math.min(from + PAGE_SIZE, shown.length)} з {shown.length}
          </span>
          <div className="row">
            <button className="btn small" disabled={current === 1} onClick={() => goTo(1)} aria-label="Перша сторінка">
              «
            </button>
            <button className="btn small" disabled={current === 1} onClick={() => goTo(current - 1)}>
              ‹ Назад
            </button>
            <span className="pager-info">
              Сторінка {current} з {pages}
            </span>
            <button className="btn small" disabled={current === pages} onClick={() => goTo(current + 1)}>
              Далі ›
            </button>
            <button className="btn small" disabled={current === pages} onClick={() => goTo(pages)} aria-label="Остання сторінка">
              »
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
