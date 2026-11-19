import { useEffect, useRef, useState } from 'react'
import { downloadText } from '../api.js'

const EXAMPLE = `[Ролі за посадою]
Developer: GitLab=developer
DevOps: GitLab=maintainer; GCP-prod=roles/editor, roles/viewer

[Конфлікти ролей]
BO: operator + refund_approver | створює й погоджує повернення

[Admin-ролі]
admin, root

[Неактивність, днів]
90`

// Правила перевірки: можна завантажити файлом або написати/відредагувати текстом.
export default function Policy({ result, policyText, onApply }) {
  const [draft, setDraft] = useState(null)
  const [open, setOpen] = useState(false)
  const fileInput = useRef(null)

  const current = policyText || result.policy_default_text
  const value = draft ?? current
  const dirty = draft !== null && draft !== current
  const error = result.policy_error
  const custom = result.policy_source === 'custom'
  const p = result.policy

  useEffect(() => {
    if (error) setOpen(true)
  }, [error])

  const apply = (text) => {
    // текст, що збігається з правилами за замовчуванням, власним не вважаємо
    onApply(text.trim() === result.policy_default_text.trim() ? '' : text)
    setDraft(null)
  }
  const onFile = async (e) => {
    const f = e.target.files[0]
    e.target.value = ''
    if (!f) return
    apply(await f.text())
    setOpen(true)
  }

  let status = <span className="badge muted">за замовчуванням (policy.json)</span>
  if (error) status = <span className="badge bad">помилка — правила не застосовано</span>
  else if (custom) status = <span className="badge info">✎ власні правила</span>

  return (
    <details className="card policy" open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>
        Правила перевірки {status}
        <span className="muted small policy-sum">
          {' '}
          · посад: {Object.keys(p.role_model).length} · конфліктів: {p.sod_conflicts.length} · admin-ролей:{' '}
          {p.admin_roles.length} · неактивність: {p.inactive_days} дн.
        </span>
      </summary>

      <p className="muted small">
        Напишіть правила текстом нижче або завантажте файл (<code>.txt</code> або <code>.json</code>). Те, що ви
        задасте, повністю замінює правила за замовчуванням з <code>policy.json</code>; розділ, якого немає, просто
        не перевіряється.
      </p>

      {error && (
        <div className="banner error">
          <strong>Правила не застосовано — аналіз іде за стандартними.</strong>
          <pre>{error}</pre>
        </div>
      )}

      <textarea
        className="policy-editor"
        value={value}
        spellCheck={false}
        rows={16}
        onChange={(e) => setDraft(e.target.value)}
      />

      <div className="row policy-actions">
        <button className="btn primary small" disabled={!dirty} onClick={() => apply(value)}>
          Застосувати
        </button>
        <button className="btn small" onClick={() => fileInput.current.click()}>
          📂 Завантажити з файлу
        </button>
        <button className="btn small" onClick={() => downloadText(value, 'policy.txt')}>
          ⬇ Зберегти у файл
        </button>
        {(policyText || dirty) && (
          <button
            className="btn small"
            onClick={() => {
              onApply('')
              setDraft(null)
            }}
          >
            ↺ Скинути до стандартних
          </button>
        )}
        {dirty && <span className="muted small">Є незастосовані зміни</span>}
      </div>
      <input ref={fileInput} type="file" hidden accept=".txt,.json,.md,.policy,text/plain" onChange={onFile} />

      <details className="help">
        <summary>Як писати правила</summary>
        <ul>
          <li>
            Правила поділено на розділи, кожен починається із заголовка в дужках. Рядки з <code>#</code> —
            коментарі.
          </li>
          <li>
            <strong>[Ролі за посадою]</strong>: <code>Посада: Система=роль1, роль2; Інша система=роль</code>. Яка роль
            дозволена на цій посаді в цій системі. Будь-яка інша роль у цій системі буде позначена. Посади, яких
            тут немає, не перевіряються.
          </li>
          <li>
            <strong>[Конфлікти ролей]</strong>: <code>Система: роль1 + роль2 | пояснення</code>. Якщо в одного
            логіна є обидві ролі в цій системі — це конфлікт.
          </li>
          <li>
            <strong>[Admin-ролі]</strong>: ролі через кому, які мають бути лише тимчасовими.
          </li>
          <li>
            <strong>[Неактивність, днів]</strong>: число. Скільки днів без входу вважається неактивним.
          </li>
          <li>Замість тексту можна завантажити JSON у форматі файлу <code>policy.json</code>.</li>
        </ul>
        <p className="muted small">Приклад:</p>
        <pre>{EXAMPLE}</pre>
      </details>
    </details>
  )
}
