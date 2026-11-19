// Надсилає файли на Python-сервер; сервер сам визначає, що є що.
export async function analyze(files, overrides, params, policyText, signal) {
  const fd = new FormData()
  files.forEach((f) => fd.append('files', f))
  fd.append('overrides', JSON.stringify(overrides))
  if (policyText && policyText.trim()) fd.append('policy', policyText)
  if (params.review_date) fd.append('review_date', params.review_date)
  if (params.inactive_days) fd.append('inactive_days', String(params.inactive_days))
  if (params.domain) fd.append('domain', params.domain)

  let res
  try {
    res = await fetch('/api/analyze', { method: 'POST', body: fd, signal })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('Не вдалося зв’язатися із сервером. Запустіть його: python -m uvicorn server:app --port 8000')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Помилка сервера (${res.status})`)
  return data
}

// Завантажує приклади з sample_data як звичайні File — далі вони проходять той самий шлях, що й ваші.
export async function loadSample() {
  return Promise.all(
    ['hr.csv', 'accounts.csv'].map(async (name) => {
      const res = await fetch(`/api/sample/${name}`)
      if (!res.ok) throw new Error('Не вдалося завантажити приклад.')
      return new File([await res.blob()], name, { type: 'text/csv' })
    }),
  )
}

// Стандартні правила текстом — щоб почати редагувати не з чистого аркуша.
export async function loadDefaultPolicyText() {
  const res = await fetch('/api/policy/text')
  if (!res.ok) throw new Error('Не вдалося завантажити стандартні правила.')
  return (await res.json()).text
}

// Excel-звіт будує сервер: надсилаємо йому знахідки (усі або відфільтровані) та підсумки.
export async function downloadXlsx(rows, result, filename = 'access_review_report.xlsx') {
  const res = await fetch('/api/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rows, summary: result.summary, params: result.params }),
  })
  if (!res.ok) throw new Error('Не вдалося сформувати Excel-звіт.')
  const url = URL.createObjectURL(await res.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}

export function downloadText(text, filename) {
  const url = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/plain;charset=utf-8' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}

export function downloadCsv(rows, filename) {
  const cols = ['system', 'login', 'email', 'role', 'issue', 'severity']
  const esc = (v) => `"${String(v ?? '').replaceAll('"', '""')}"`
  const text = [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\r\n')
  const url = URL.createObjectURL(new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}
