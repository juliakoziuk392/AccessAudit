import { useEffect, useRef, useState } from 'react'
import { loadDefaultPolicyText } from '../api.js'

const fmtSize = (n) => (n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} МБ` : `${Math.max(1, Math.round(n / 1024))} КБ`)

const POLICY_PLACEHOLDER = `[Ролі за посадою]
Developer: GitLab=developer
Manager: BO=viewer

[Конфлікти ролей]
BO: operator + refund_approver | створює й погоджує повернення

[Admin-ролі]
admin

[Неактивність, днів]
90`

export default function Dropzone({
  files,
  onFiles,
  onSample,
  loading,
  policyText,
  policyName,
  onPolicyFile,
  onPolicyText,
  onPolicyClear,
}) {
  const input = useRef(null)
  const policyInput = useRef(null)
  const [drag, setDrag] = useState(false)
  const [draft, setDraft] = useState(null) // незастосований текст у полі; null = збігається із застосованим
  const [textError, setTextError] = useState(null)
  const compact = files.length === 2

  const value = draft ?? policyText
  const dirty = draft !== null && draft !== policyText
  // правила змінились ззовні (файл, «×») — поле показує їх, а не старий чернетковий текст
  useEffect(() => setDraft(null), [policyText])

  const fillDefault = async () => {
    try {
      setDraft(await loadDefaultPolicyText())
      setTextError(null)
    } catch (e) {
      setTextError(e.message)
    }
  }

  const pick = (list) => {
    const arr = Array.from(list || []).filter((f) => /\.(csv|txt|xlsx|xls)$/i.test(f.name))
    if (arr.length) onFiles(arr)
  }
  // .json / .policy, кинуті в зону, — це файл правил (дані бувають лише csv/txt/xlsx/xls)
  const drop = (list) => {
    const all = Array.from(list || [])
    const policy = all.find((f) => /\.(json|policy)$/i.test(f.name))
    if (policy) onPolicyFile(policy)
    pick(all.filter((f) => f !== policy))
  }

  return (
    <section
      className={`card dropzone ${drag ? 'drag' : ''} ${compact ? 'compact' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDrag(true)
      }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDrag(false)
        drop(e.dataTransfer.files)
      }}
    >
      {!compact && (
        <div className="dz-body">
          <div className="dz-icon">📂</div>
          <h2>{files.length === 0 ? 'Перетягніть сюди 2 файли' : 'Додайте ще один файл'}</h2>
          <p className="muted">CSV або Excel (.xlsx). Порядок неважливий, колонки можуть називатись як завгодно.</p>
          <div className="row center">
            <button className="btn primary" onClick={() => input.current.click()}>
              Обрати файли
            </button>
            {files.length === 0 && (
              <button className="btn" onClick={onSample}>
                Спробувати на прикладі
              </button>
            )}
          </div>
        </div>
      )}

      {files.length > 0 && (
        <div className="chips">
          {files.map((f) => (
            <span className="chip" key={f.name + f.size}>
              📄 {f.name} <span className="muted">· {fmtSize(f.size)}</span>
            </span>
          ))}
          {compact && (
            <>
              <button className="btn small" onClick={() => input.current.click()}>
                Замінити файл
              </button>
              {loading && <span className="muted">аналізую…</span>}
            </>
          )}
        </div>
      )}

      <div className="dz-policy">
        <span className="dz-policy-label">
          📋 Правила перевірки <span className="muted">(необов’язково)</span>
        </span>
        {policyText ? (
          <span className="chip">
            📋 {policyName || 'власні правила'}
            <button className="chip-x" onClick={onPolicyClear} aria-label="Прибрати правила" title="Прибрати правила">
              ×
            </button>
          </span>
        ) : (
          <span className="muted small">не додано — діють стандартні (policy.json)</span>
        )}
        <button className="btn small" onClick={() => policyInput.current.click()}>
          {policyText ? 'Замінити файл правил' : 'Додати файл правил'}
        </button>
        {!compact && !policyText && (
          <span className="muted small dz-policy-hint">
            .txt або .json: яка роль дозволена на кожній посаді, конфлікти ролей, admin-ролі, дні неактивності
          </span>
        )}
      </div>

      {/* до завантаження файлів поле видно завжди; коли обидва файли вже є — згортається (якщо правил немає) */}
      <details className={`dz-policy-text ${compact ? '' : 'static'}`} open={!compact || !!policyText}>
        <summary onClick={(e) => !compact && e.preventDefault()}>✎ Або напишіть правила текстом</summary>
        <textarea
          className="policy-editor"
          value={value}
          placeholder={POLICY_PLACEHOLDER}
          spellCheck={false}
          rows={12}
          onChange={(e) => setDraft(e.target.value)}
        />
        <div className="row dz-policy-actions">
          <button
            className="btn primary small"
            disabled={!dirty}
            onClick={() => {
              onPolicyText(draft)
              setDraft(null)
            }}
          >
            Застосувати
          </button>
          <button className="btn small" onClick={fillDefault}>
            Підставити стандартні правила
          </button>
          {(value || policyText) && (
            <button
              className="btn small"
              onClick={() => {
                onPolicyClear()
                setDraft(null)
              }}
            >
              ↺ Очистити
            </button>
          )}
          {dirty && <span className="muted small">Є незастосовані зміни</span>}
          {textError && <span className="small dz-err">{textError}</span>}
        </div>
        <p className="muted small">
          Формат: розділи в дужках — <code>[Ролі за посадою]</code>, <code>[Конфлікти ролей]</code>,{' '}
          <code>[Admin-ролі]</code>, <code>[Неактивність, днів]</code>.
          {files.length < 2 && ' Правила застосуються, щойно завантажите два файли.'}
        </p>
      </details>

      <input
        ref={policyInput}
        type="file"
        hidden
        accept=".txt,.json,.md,.policy,text/plain"
        onChange={(e) => {
          const f = e.target.files[0]
          e.target.value = ''
          if (f) onPolicyFile(f)
        }}
      />

      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept=".csv,.txt,.xlsx,.xls"
        onChange={(e) => {
          pick(e.target.files)
          e.target.value = ''
        }}
      />
    </section>
  )
}
