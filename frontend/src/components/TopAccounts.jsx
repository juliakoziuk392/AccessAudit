export default function TopAccounts({ rows }) {
  return (
    <section className="card">
      <h3>Найризикованіші акаунти</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Система</th>
              <th>Логін</th>
              <th className="num">Знахідок</th>
              <th className="num">Бали</th>
              <th>Проблеми</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.system + r.login}>
                <td>{r.system}</td>
                <td>
                  <strong>{r.login}</strong>
                  {r.employee && <div className="muted small">{r.employee}</div>}
                </td>
                <td className="num">{r.findings}</td>
                <td className="num">{r.score}</td>
                <td>
                  {r.types.map((t) => (
                    <span className="tag" key={t}>
                      {t}
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">Бали: критична знахідка = 3, середня = 2, низька = 1.</p>
    </section>
  )
}
