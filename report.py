"""Формування Excel-звіту (.xlsx) зі знахідок."""
import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SEV_FILL = {"Критично": "F8C9CB", "Середньо": "FDE3B0", "Низько": "FBF0B5"}
COLUMNS = [("severity", "Критичність", 14), ("system", "Система", 12), ("login", "Логін", 26),
           ("email", "Email", 32), ("employee", "ПІБ", 24), ("position", "Посада", 18),
           ("role", "Роль", 28), ("created", "Дата реєстрації", 16), ("last_login", "Останній вхід", 16),
           ("issue", "Проблема", 48)]
DATE_KEYS = ("created", "last_login")
HEADER_FILL = PatternFill("solid", fgColor="5B5BD6")


def _cell(ws, row, col, value):
    """Клітинка з даними. Текст, що починається з «=», лишається текстом, а не формулою."""
    c = ws.cell(row=row, column=col)
    c.value = "" if value is None else value
    if isinstance(c.value, str) and c.value.startswith("="):
        c.data_type = "s"
    return c


def _header(ws, row, titles):
    for i, t in enumerate(titles, 1):
        c = ws.cell(row=row, column=i, value=t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEADER_FILL
        c.alignment = Alignment(vertical="center")


def build_xlsx(rows: list[dict], summary: dict | None = None, params: dict | None = None) -> bytes:
    summary, params = summary or {}, params or {}
    wb = Workbook()

    # --- Лист 1: усі знахідки
    ws = wb.active
    ws.title = "Знахідки"
    # колонка «Дата реєстрації» потрібна лише якщо вона була у вхідному файлі
    cols = [c for c in COLUMNS if c[0] != "created" or any(r.get("created") for r in rows)]
    _header(ws, 1, [c[1] for c in cols])
    for r, row in enumerate(rows, 2):
        for i, (key, _, _) in enumerate(cols, 1):
            value = row.get(key)
            if key in DATE_KEYS and value:
                # справжня дата, а не текст: працюють сортування й фільтр Excel
                try:
                    value = date.fromisoformat(str(value)[:10])
                except ValueError:
                    pass
            cell = _cell(ws, r, i, value)
            if isinstance(value, date):
                cell.number_format = "DD.MM.YYYY"
                cell.alignment = Alignment(horizontal="left")
            if key == "severity" and row.get(key) in SEV_FILL:
                cell.fill = PatternFill("solid", fgColor=SEV_FILL[row[key]])
                cell.font = Font(bold=True)
    for i, (_, _, width) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{max(len(rows) + 1, 2)}"

    # --- Лист 2: підсумок
    s = wb.create_sheet("Підсумок")
    s.column_dimensions["A"].width = 34
    s.column_dimensions["B"].width = 16
    s.column_dimensions["C"].width = 12
    line = 1

    def put(label, value=None, bold=False):
        nonlocal line
        a = _cell(s, line, 1, label)
        if bold:
            a.font = Font(bold=True)
        if value is not None:
            _cell(s, line, 2, value)
        line += 1

    put("Access Review: підсумок", bold=True)
    s["A1"].font = Font(bold=True, size=14)
    line += 1
    put("Дата рев'ю", params.get("review_date"))
    put("Поріг неактивності, днів", params.get("inactive_days"))
    put("Корпоративний домен", params.get("domain"))
    line += 1
    put("Перевірено акаунтів", summary.get("accounts_total"))
    put("Акаунтів із проблемами", summary.get("accounts_flagged"))
    put("Усього знахідок", summary.get("findings"))
    put("Критичних", summary.get("critical"))
    if summary.get("findings") is not None and len(rows) != summary["findings"]:
        put(f"У звіті {len(rows)} із {summary['findings']} знахідок (застосовано фільтри)", bold=True)
    for title, key, first in (("Знахідки за типом", "by_type", "Тип"),
                              ("Знахідки за системою", "by_system", "Система")):
        items = summary.get(key) or []
        if not items:
            continue
        line += 1
        put(title, bold=True)
        _header(s, line, [first, "Критичність", "Кількість"])
        line += 1
        for it in items:
            name = it.get("type") or it.get("system")
            _cell(s, line, 1, name)
            sev = _cell(s, line, 2, it.get("severity"))
            if it.get("severity") in SEV_FILL:
                sev.fill = PatternFill("solid", fgColor=SEV_FILL[it["severity"]])
            _cell(s, line, 3, it.get("count"))
            line += 1

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
