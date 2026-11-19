import { useEffect, useRef, useState } from 'react'
import { analyze, downloadXlsx, loadSample } from './api.js'
import Dropzone from './components/Dropzone.jsx'
import Detection from './components/Detection.jsx'
import Settings from './components/Settings.jsx'
import Kpis from './components/Kpis.jsx'
import Charts from './components/Charts.jsx'
import TopAccounts from './components/TopAccounts.jsx'
import FindingsTable from './components/FindingsTable.jsx'
import Policy from './components/Policy.jsx'

const NO_PARAMS = { review_date: '', inactive_days: '', domain: '' }
const POLICY_KEY = 'access-review.policy'
const POLICY_NAME_KEY = 'access-review.policy-name'

export default function App() {
  const [files, setFiles] = useState([])
  const [overrides, setOverrides] = useState({})
  const [params, setParams] = useState(NO_PARAMS)
  // Власні правила (текст). Порожньо = правила за замовчуванням із policy.json.
  const [policyText, setPolicyTextState] = useState(() => localStorage.getItem(POLICY_KEY) || '')
  // Ім’я файлу правил — лише для підпису в зоні завантаження (порожньо, якщо правила написано вручну).
  const [policyName, setPolicyNameState] = useState(() => localStorage.getItem(POLICY_NAME_KEY) || '')
  const setPolicyText = (text, name = '') => {
    const has = text.trim() !== ''
    setPolicyTextState(text)
    setPolicyNameState(has ? name : '')
    if (has) localStorage.setItem(POLICY_KEY, text)
    else localStorage.removeItem(POLICY_KEY)
    if (has && name) localStorage.setItem(POLICY_NAME_KEY, name)
    else localStorage.removeItem(POLICY_NAME_KEY)
  }
  const loadPolicyFile = async (file) => setPolicyText(await file.text(), file.name)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const seq = useRef(0)

  // Будь-яка зміна файлів / ручного зіставлення / параметрів — перераховуємо (з невеликою затримкою).
  useEffect(() => {
    if (files.length !== 2) {
      setResult(null)
      setError(null)
      return
    }
    const ctrl = new AbortController()
    const id = ++seq.current
    setLoading(true)
    const t = setTimeout(async () => {
      try {
        const data = await analyze(files, overrides, params, policyText, ctrl.signal)
        if (id === seq.current) {
          setResult(data)
          setError(null)
        }
      } catch (e) {
        if (e.name !== 'AbortError' && id === seq.current) {
          setResult(null)
          setError(e.message)
        }
      } finally {
        if (id === seq.current) setLoading(false)
      }
    }, 250)
    return () => {
      clearTimeout(t)
      ctrl.abort()
    }
  }, [files, overrides, params, policyText])

  const reset = () => {
    setFiles([])
    setOverrides({})
    setParams(NO_PARAMS)
  }
  const addFiles = (list) => {
    setOverrides({})
    setParams(NO_PARAMS)
    setFiles((prev) => [...prev, ...list].slice(-2))
  }
  const useSample = async () => {
    try {
      addFiles(await loadSample())
    } catch (e) {
      setError(e.message)
    }
  }

  const exportXlsx = async (rows) => {
    try {
      await downloadXlsx(rows, result)
    } catch (e) {
      setError(e.message)
    }
  }

  const setColumn = (kind, field, column) =>
    setOverrides((o) => ({
      ...o,
      columns: { ...o.columns, [kind]: { ...o.columns?.[kind], [field]: column || null } },
    }))
  const swapFiles = () => {
    if (!result) return
    setOverrides({ roles: { hr: result.files.accounts.index, accounts: result.files.hr.index } })
  }

  return (
    <div className="page">
      <header className="top">
        <div>
          <h1>🔐 Access Review</h1>
          <p className="muted">
            Завантажте два файли — вивантаження з HR і список акаунтів. Програма сама визначить, що є що,
            які там колонки, і покаже ризики.
          </p>
        </div>
        <div className="row">
          {result?.ok && (
            <button className="btn primary" onClick={() => exportXlsx(result.findings)}>
              ⬇ Завантажити звіт Excel
            </button>
          )}
          {files.length > 0 && (
            <button className="btn" onClick={reset}>
              ↺ Почати спочатку
            </button>
          )}
        </div>
      </header>

      <Dropzone
        files={files}
        onFiles={addFiles}
        onSample={useSample}
        loading={loading}
        policyText={policyText}
        policyName={policyName}
        onPolicyFile={loadPolicyFile}
        onPolicyText={(text) => setPolicyText(text)}
        onPolicyClear={() => setPolicyText('')}
      />

      {error && <div className="banner error">⚠️ {error}</div>}

      {result?.policy_error && (
        <div className="banner error">
          <strong>Файл правил не застосовано — аналіз іде за стандартними правилами.</strong>
          <pre>{result.policy_error}</pre>
        </div>
      )}

      {result && (
        <>
          <Detection
            files={result.files}
            onColumn={setColumn}
            onSwap={swapFiles}
            errors={result.ok ? [] : result.errors}
          />

          {result.ok && (
            <>
              <Settings
                params={result.params}
                custom={params}
                onChange={(patch) => setParams((p) => ({ ...p, ...patch }))}
              />
              {result.warnings.length > 0 && (
                <div className="banner warn">
                  <strong>Зверніть увагу</strong>
                  <ul>
                    {result.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
              <Kpis summary={result.summary} />
              {result.summary.findings === 0 ? (
                <div className="banner ok">Проблем не знайдено 🎉</div>
              ) : (
                <>
                  <Charts summary={result.summary} />
                  <TopAccounts rows={result.top_accounts} />
                  <FindingsTable rows={result.findings} onExcel={exportXlsx} />
                </>
              )}
              <Policy result={result} policyText={policyText} onApply={setPolicyText} />
            </>
          )}
        </>
      )}
    </div>
  )
}
