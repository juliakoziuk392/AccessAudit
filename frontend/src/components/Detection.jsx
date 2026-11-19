const KIND_TITLE = { hr: '👥 HR-файл', accounts: '🔑 Файл акаунтів' }

function Badge({ field }) {
  if (field.overridden) return <span className="badge info">вручну</span>
  if (!field.column) return <span className={`badge ${field.required ? 'bad' : 'muted'}`}>не знайдено</span>
  if (field.score >= 1) return <span className="badge good">✓ впевнено</span>
  return <span className="badge warn">перевірте</span>
}

function FileCard({ kind, info, onColumn }) {
  return (
    <div className="card file-card">
      <div className="file-head">
        <div>
          <h3>{KIND_TITLE[kind]}</h3>
          <div className="muted small">
            {info.name} · {info.rows} рядків · {info.columns.length} колонок
          </div>
        </div>
      </div>
      <table className="map">
        <thead>
          <tr>
            <th>Що це</th>
            <th>Колонка у файлі</th>
            <th>Приклад значення</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {info.fields.map((f) => (
            <tr key={f.key}>
              <td>
                {f.label}
                {f.required && <span className="req"> *</span>}
              </td>
              <td>
                <select value={f.column || ''} onChange={(e) => onColumn(kind, f.key, e.target.value)}>
                  <option value="">— немає —</option>
                  {info.columns.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </td>
              <td className="sample">{f.sample ?? <span className="muted">—</span>}</td>
              <td>
                <Badge field={f} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Detection({ files, onColumn, onSwap, errors }) {
  return (
    <section>
      <div className="section-head">
        <h2>Що ми знайшли у файлах</h2>
        <button className="btn small" onClick={onSwap} title="Якщо програма переплутала файли">
          ⇄ Поміняти місцями HR і акаунти
        </button>
      </div>
      {errors.length > 0 && (
        <div className="banner error">
          {errors.map((e) => (
            <div key={e}>⚠️ {e}</div>
          ))}
        </div>
      )}
      <div className="grid-2">
        <FileCard kind="hr" info={files.hr} onColumn={onColumn} />
        <FileCard kind="accounts" info={files.accounts} onColumn={onColumn} />
      </div>
      <p className="muted small">
        * обов’язкові поля. Якщо колонку визначено неправильно — виберіть потрібну зі списку, звіт оновиться одразу.
      </p>
    </section>
  )
}
