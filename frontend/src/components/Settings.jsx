// Параметри перевірки. Порожнє поле = «визначити автоматично».
export default function Settings({ params, custom, onChange }) {
  return (
    <section className="card settings">
      <label>
        <span>Дата рев’ю</span>
        <input
          type="date"
          value={custom.review_date || params.review_date}
          onChange={(e) => onChange({ review_date: e.target.value })}
        />
      </label>
      <label>
        <span>Неактивний після (днів)</span>
        <input
          type="number"
          min="1"
          max="3650"
          value={custom.inactive_days || params.inactive_days}
          onChange={(e) => onChange({ inactive_days: e.target.value })}
        />
      </label>
      <label>
        <span>
          Корпоративний домен <span className="muted small">(визначено з HR автоматично)</span>
        </span>
        <input
          type="text"
          value={custom.domain}
          placeholder={params.domain_detected || '@company.com'}
          onChange={(e) => onChange({ domain: e.target.value })}
        />
      </label>
    </section>
  )
}
