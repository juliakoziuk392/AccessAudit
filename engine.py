"""Рушій access review (раніше lesson1.py).

Сам визначає, який із двох файлів HR, а який — список акаунтів, і яка колонка
що означає (за назвою та за вмістом). Правила перевірок беруться з policy.json.

Як бібліотека:   engine.run([(ім'я, байти), (ім'я, байти)]) -> dict
Як CLI:          python -X utf8 engine.py файл1.csv файл2.csv [--date 2026-11-17] [-o report.csv]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

POLICY_PATH = Path(__file__).with_name("policy.json")


class AnalysisError(Exception):
    """Помилка, яку можна показати користувачу."""


# --------------------------------------------------------------------------
# Поля, які ми шукаємо у файлах
# --------------------------------------------------------------------------
HR_FIELDS = ["email", "emp_id", "status", "position", "name"]
ACC_FIELDS = ["email", "system", "login", "role", "last_login", "created"]
REQUIRED = {"hr": ["email"], "accounts": ["email", "system", "login", "role"]}
FIELD_LABELS = {
    "email": "Email", "emp_id": "Табельний №", "status": "Статус працівника",
    "position": "Посада", "name": "ПІБ", "system": "Система", "login": "Логін",
    "role": "Роль", "last_login": "Останній вхід", "created": "Дата реєстрації",
}
# Для визначення типу файлу беремо не email (він є в обох), а решту полів.
KIND_FIELDS = {
    "hr": ["emp_id", "status", "position", "name"],
    "accounts": ["system", "login", "role", "last_login"],
}
ALL_FIELDS = ["email", "system", "login", "role", "last_login", "created",
              "emp_id", "status", "position", "name"]

# Можливі назви колонок (у нормалізованому вигляді: нижній регістр, _ замість розділювачів).
ALIASES = {
    "email": ["email", "e_mail", "mail", "email_address", "corporate_email", "user_email",
              "work_email", "пошта", "електронна_пошта", "ел_пошта", "почта"],
    "emp_id": ["emp_id", "empid", "employee_id", "employee_number", "employee_no", "staff_id",
               "personnel_number", "hr_id", "табельний", "табельний_номер", "id_працівника",
               "табельный_номер"],
    "status": ["status", "employment_status", "emp_status", "hr_status", "статус", "стан",
               "статус_працівника"],
    "position": ["position", "job_title", "jobtitle", "title", "role_title", "job", "посада",
                 "должность"],
    "name": ["name", "full_name", "fullname", "employee_name", "піб", "ім_я", "прізвище_імя",
             "фио"],
    "system": ["system", "application", "app", "service", "resource", "platform", "система",
               "застосунок", "сервіс", "ресурс"],
    "login": ["login", "username", "user_name", "user", "account", "account_name", "user_id",
              "userid", "login_name", "логін", "користувач", "акаунт"],
    "role": ["role", "access_level", "permission", "permissions", "privilege", "group",
             "access_role", "роль", "права", "рівень_доступу"],
    "last_login": ["last_login", "lastlogin", "last_login_date", "last_activity", "last_seen",
                   "last_access", "last_signin", "last_sign_in", "last_logon", "остання_активність",
                   "останній_вхід", "дата_останнього_входу"],
    # Дата реєстрації/створення акаунта. Необов'язкова; впізнається лише за назвою колонки
    # (за самими датами її не відрізнити від «останнього входу»).
    "created": ["created", "created_at", "created_date", "date_created", "creation_date",
                "account_created", "registered", "registered_at", "registration_date",
                "registration", "reg_date", "signup_date", "sign_up_date", "joined",
                "joined_at", "date_joined", "дата_реєстрації", "реєстрація", "зареєстровано",
                "дата_створення", "створено", "створений"],
}

# Значення статусу працівника (у нормалізованому вигляді: розділювачі -> пробіл).
STATUS_VOCAB = {
    "terminated": {"terminated", "fired", "dismissed", "resigned", "left", "звільнений",
                   "звільнена", "звільнено", "уволен", "уволенный", "уволена"},
    "leave": {"leave", "on leave", "vacation", "on vacation", "maternity", "maternity leave",
              "parental leave", "sick", "sick leave", "відпустка", "у відпустці", "на відпустці",
              "декрет", "лікарняний", "в отпуске", "отпуск"},
    "active": {"active", "employed", "current", "working", "активний", "активна", "працює",
               "діючий", "работает", "активен"},
}

# Критичність і назви типів знахідок
SEVERITY = {
    "terminated": "Критично", "no_hr": "Критично", "sod": "Критично", "admin": "Критично",
    "role_mismatch": "Середньо", "inactive": "Середньо", "bad_email": "Середньо",
    "leave": "Низько",
}
CATEGORY_TITLE = {
    "terminated": "Звільнений працівник", "no_hr": "Немає працівника в HR",
    "sod": "Конфлікт ролей (SoD)", "admin": "Постійна admin-роль",
    "role_mismatch": "Роль не відповідає посаді", "inactive": "Неактивний акаунт",
    "bad_email": "Некорпоративна пошта", "leave": "Працівник у відпустці",
}
SEVERITY_ORDER = ["Критично", "Середньо", "Низько"]
SEVERITY_WEIGHT = {"Критично": 3, "Середньо": 2, "Низько": 1}


# --------------------------------------------------------------------------
# Читання файлів
# --------------------------------------------------------------------------
def read_table(name: str, data: bytes) -> pd.DataFrame:
    """Читає CSV (будь-який роздільник/кодування) або Excel у таблицю з рядків."""
    try:
        if Path(name).suffix.lower() in (".xlsx", ".xlsm", ".xls"):
            df = pd.read_excel(io.BytesIO(data), dtype=str)
        else:
            text = None
            for enc in ("utf-8-sig", "cp1251", "cp1250", "latin-1"):
                try:
                    text = data.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str,
                             skipinitialspace=True)
    except Exception as e:
        raise AnalysisError(f"Не вдалося прочитати файл «{name}»: {e}") from e

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df = df.apply(lambda s: s.str.strip())
    df = df.mask(df.eq(""))
    if df.shape[1] < 2 or df.empty:
        raise AnalysisError(f"Файл «{name}» порожній або має менше двох колонок.")
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------
# Автовизначення колонок
# --------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"^\d{1,4}[-./]\d{1,2}[-./]\d{1,4}")


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-zа-яіїєґё]+", "_", str(s).lower().strip()).strip("_")


def status_of(value) -> str | None:
    """'terminated' / 'leave' / 'active' або None, якщо значення невідоме."""
    n = re.sub(r"[\s_\-]+", " ", str(value).strip().lower())
    for key, vocab in STATUS_VOCAB.items():
        if n in vocab:
            return key
    return None


def _header_score(col: str, aliases: list[str]) -> float:
    n = _norm(col)
    if n in aliases:
        return 1.0
    for a in aliases:
        if len(a) >= 4 and len(n) >= 4 and (a in n or n in a):
            return 0.6
    return 0.0


def _content_score(field: str, series: pd.Series) -> float:
    vals = series.dropna().astype(str).head(500)
    if vals.empty:
        return 0.0
    if field == "email":
        share = vals.map(lambda v: bool(EMAIL_RE.match(v))).mean()
        return float(share) if share >= 0.5 else 0.0
    if field == "last_login":
        share = vals.map(lambda v: bool(DATE_RE.match(v))).mean()
        return 0.9 * float(share) if share >= 0.8 else 0.0
    if field == "status":
        share = vals.map(lambda v: status_of(v) is not None).mean()
        return float(share) if share >= 0.6 else 0.0
    return 0.0


def _looks_like_dates(series: pd.Series) -> bool:
    vals = series.dropna().astype(str).head(500)
    return not vals.empty and vals.map(lambda v: bool(DATE_RE.match(v))).mean() >= 0.8


def assign_columns(df: pd.DataFrame, fields: list[str], min_score: float = 0.5) -> dict:
    """Жадібно зіставляє поля з колонками за найкращою оцінкою. -> {поле: (колонка, оцінка)}"""
    cands = []
    for fi, field in enumerate(fields):
        for ci, col in enumerate(df.columns):
            if field == "created" and not _looks_like_dates(df[col]):
                continue  # напр. «created_by» назвою схоже, але це не дата
            score = _header_score(col, ALIASES[field]) + _content_score(field, df[col])
            if score >= min_score:
                cands.append((-score, fi, ci, field, col))
    cands.sort()
    out, used = {}, set()
    for neg, _, _, field, col in cands:
        if field in out or col in used:
            continue
        out[field] = (col, -neg)
        used.add(col)
    return out


def detect_kinds(tables: list[pd.DataFrame]) -> tuple[int, int]:
    """Повертає (індекс HR-файлу, індекс файлу акаунтів)."""
    def kind_score(df, kind):
        m = assign_columns(df, ALL_FIELDS)
        return sum(m[f][1] for f in KIND_FIELDS[kind] if f in m)

    a = kind_score(tables[0], "hr") + kind_score(tables[1], "accounts")
    b = kind_score(tables[1], "hr") + kind_score(tables[0], "accounts")
    if abs(a - b) < 1e-9:
        raise AnalysisError("Не вдалося визначити, який файл HR, а який — список акаунтів. "
                            "Вкажіть це вручну.")
    return (0, 1) if a > b else (1, 0)


def build_mapping(df: pd.DataFrame, kind: str, override: dict | None) -> dict:
    """{поле: {column, score, overridden}} з урахуванням ручних виправлень."""
    fields = HR_FIELDS if kind == "hr" else ACC_FIELDS
    auto = assign_columns(df, fields)
    override = override or {}
    mapping = {}
    for f in fields:
        if f in override:
            col = override[f] if override[f] in df.columns else None
            mapping[f] = {"column": col, "score": 1.0 if col else 0.0, "overridden": True}
        elif f in auto:
            mapping[f] = {"column": auto[f][0], "score": round(auto[f][1], 2), "overridden": False}
        else:
            mapping[f] = {"column": None, "score": 0.0, "overridden": False}
    # логін часто збігається з поштою
    if kind == "accounts" and not mapping["login"]["column"] and mapping["email"]["column"] \
            and "login" not in override:
        mapping["login"] = {"column": mapping["email"]["column"], "score": 0.5, "overridden": False}
    return mapping


# --------------------------------------------------------------------------
# Допоміжні перетворення
# --------------------------------------------------------------------------
def parse_dates(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    iso = s.str.match(r"^\d{4}-\d{1,2}-\d{1,2}", na=False)
    a = pd.to_datetime(s.where(iso), errors="coerce", format="ISO8601", utc=True)
    b = pd.to_datetime(s.where(~iso & s.notna()), errors="coerce", dayfirst=True,
                       format="mixed", utc=True)
    return a.fillna(b).dt.tz_localize(None)


def _date_str(v) -> str | None:
    """Дата як «РРРР-ММ-ДД» (або None). Рядком, щоб pandas не віддав її числом у JSON."""
    return None if pd.isna(v) else v.strftime("%Y-%m-%d")


def _key(v) -> str:
    return re.sub(r"\s+", " ", str(v).strip().lower())


def _norm_domain(d: str | None) -> str:
    d = (d or "").strip().lower()
    return "" if not d else (d if d.startswith("@") else "@" + d)


def detect_domain(emails: pd.Series) -> str:
    domains = [str(e).rsplit("@", 1)[1] for e in emails.dropna() if "@" in str(e)]
    return "@" + Counter(domains).most_common(1)[0][0] if domains else ""


def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Правила: читання з тексту / JSON і запис назад у текст
# --------------------------------------------------------------------------
# Заголовок розділу -> що це за розділ (за ключовими словами, укр/англ).
_SECTIONS = [
    ("sod", ("конфлікт", "conflict", "sod")),
    ("admin", ("admin", "адмін")),
    ("inactive", ("неактив", "inactive")),
    ("roles", ("посад", "role", "ролі")),
]
_SECTION_HINT = "[Ролі за посадою], [Конфлікти ролей], [Admin-ролі], [Неактивність, днів]"


def _section_of(title: str) -> str | None:
    t = title.lower()
    for key, words in _SECTIONS:
        if any(w in t for w in words):
            return key
    return None


def _empty_policy() -> dict:
    return {"inactive_days": int(load_policy().get("inactive_days", 90)),
            "admin_roles": [], "role_model": {}, "sod_conflicts": []}


def validate_policy(data) -> dict:
    """Перевіряє й нормалізує правила, задані як JSON-об'єкт."""
    try:
        if not isinstance(data, dict):
            raise TypeError
        out = _empty_policy()
        if "inactive_days" in data:
            out["inactive_days"] = int(data["inactive_days"])
        out["admin_roles"] = [str(r) for r in data.get("admin_roles", [])]
        for pos, systems in data.get("role_model", {}).items():
            out["role_model"][str(pos)] = {
                str(s): [str(x) for x in ([roles] if isinstance(roles, str) else roles)]
                for s, roles in systems.items()}
        for c in data.get("sod_conflicts", []):
            roles = [str(x) for x in c["roles"]]
            if len(roles) < 2:
                raise ValueError
            out["sod_conflicts"].append({
                "system": str(c["system"]), "roles": roles,
                "reason": str(c.get("reason") or "конфлікт ролей: " + " + ".join(roles))})
        return out
    except (TypeError, ValueError, KeyError, AttributeError) as e:
        raise AnalysisError("JSON-правила мають неправильну структуру. Очікується: inactive_days, "
                            "admin_roles, role_model, sod_conflicts (див. policy.json).") from e


def parse_policy_text(text: str) -> dict:
    """Правила з тексту (розділи в [дужках]) або з JSON."""
    text = text.lstrip("﻿")
    if text.lstrip().startswith("{"):
        try:
            return validate_policy(json.loads(text))
        except json.JSONDecodeError as e:
            raise AnalysisError(f"JSON: {e.msg} (рядок {e.lineno})") from e

    policy, section, errors = _empty_policy(), None, []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.fullmatch(r"\[(.+)\]", line)
        if m:
            section = _section_of(m.group(1))
            if section is None:
                errors.append(f"Рядок {n}: невідомий розділ «{m.group(1)}». Доступні: {_SECTION_HINT}")
            continue
        if section is None:
            errors.append(f"Рядок {n}: спочатку вкажіть розділ, наприклад [Ролі за посадою]")
            continue

        if section == "roles":
            pos, _, rest = line.partition(":")
            entries = [c.strip() for c in rest.split(";") if c.strip()]
            if not pos.strip() or not entries:
                errors.append(f"Рядок {n}: очікується «Посада: Система=роль1, роль2; Система2=роль»")
                continue
            for entry in entries:
                system, eq, roles = entry.partition("=")
                roles = [r.strip() for r in roles.split(",") if r.strip()]
                if not eq or not system.strip() or not roles:
                    errors.append(f"Рядок {n}: «{entry}» — очікується «Система=роль1, роль2»")
                    continue
                policy["role_model"].setdefault(pos.strip(), {}).setdefault(system.strip(), []).extend(roles)
        elif section == "sod":
            left, _, reason = line.partition("|")
            system, _, roles = left.partition(":")
            roles = [r.strip() for r in roles.split("+") if r.strip()]
            if not system.strip() or len(roles) < 2:
                errors.append(f"Рядок {n}: очікується «Система: роль1 + роль2 | пояснення»")
                continue
            policy["sod_conflicts"].append({
                "system": system.strip(), "roles": roles,
                "reason": reason.strip() or "конфлікт ролей: " + " + ".join(roles)})
        elif section == "admin":
            policy["admin_roles"] += [r.strip() for r in line.split(",") if r.strip()]
        elif section == "inactive":
            if line.isdigit() and 1 <= int(line) <= 3650:
                policy["inactive_days"] = int(line)
            else:
                errors.append(f"Рядок {n}: очікується число днів (1–3650), а не «{line}»")
    if errors:
        raise AnalysisError("\n".join(errors[:6]) + (f"\n…та ще {len(errors) - 6}" if len(errors) > 6 else ""))
    return policy


def policy_to_text(policy: dict) -> str:
    """Правила у вигляді тексту, який можна редагувати й завантажувати назад."""
    out = ["# Правила перевірки доступів. Рядки, що починаються з #, — коментарі.", "",
           "[Ролі за посадою]", "# Посада: Система=роль1, роль2; Інша система=роль"]
    for pos, systems in policy.get("role_model", {}).items():
        out.append(f"{pos}: " + "; ".join(f"{s}={', '.join(r)}" for s, r in systems.items()))
    out += ["", "[Конфлікти ролей]", "# Система: роль1 + роль2 | пояснення"]
    for c in policy.get("sod_conflicts", []):
        out.append(f"{c['system']}: {' + '.join(c['roles'])} | {c.get('reason', '')}".rstrip(" |"))
    out += ["", "[Admin-ролі]", "# Ролі, які мають видаватись лише тимчасово (через PAM), через кому",
            ", ".join(policy.get("admin_roles", [])) if policy.get("admin_roles") else "# (немає)",
            "", "[Неактивність, днів]", str(policy.get("inactive_days", 90)), ""]
    return "\n".join(out)


# --------------------------------------------------------------------------
# Перевірки
# --------------------------------------------------------------------------
def analyze(hr: pd.DataFrame, acc: pd.DataFrame, hm: dict, am: dict, policy: dict,
            review_date: pd.Timestamp, inactive_days: int, domain: str):
    """Застосовує правила. Повертає (DataFrame знахідок, попередження, доп. дані)."""
    warnings: list[str] = []
    col = lambda m, f: m[f]["column"]

    # --- HR -> стандартні колонки
    hrs = pd.DataFrame({"email": hr[col(hm, "email")].str.lower()})
    for f in ("status", "position", "name"):
        hrs[f] = hr[col(hm, f)] if col(hm, f) else pd.NA
    hrs = hrs.dropna(subset=["email"])
    dup = int(hrs.duplicated("email").sum())
    if dup:
        warnings.append(f"У HR-файлі {dup} дублікатів пошти — взято перший запис для кожної.")
        hrs = hrs.drop_duplicates("email")
    if not col(hm, "status"):
        warnings.append("У HR-файлі не знайдено колонку зі статусом — перевірки «звільнений» і «відпустка» пропущено.")
    else:
        raw = hrs["status"].dropna()
        unknown = sorted({str(v) for v in raw if status_of(v) is None})
        hrs["status"] = hrs["status"].map(lambda v: status_of(v) if pd.notna(v) else None)
        if unknown:
            warnings.append("Невідомі статуси (вважаю їх «активний»): " + ", ".join(unknown[:6]) +
                            ("…" if len(unknown) > 6 else ""))
    if not col(hm, "position"):
        warnings.append("У HR-файлі не знайдено колонку з посадою — перевірку «роль відповідає посаді» пропущено.")

    # --- Акаунти -> стандартні колонки
    accs = pd.DataFrame({
        "system": acc[col(am, "system")], "login": acc[col(am, "login")],
        "role": acc[col(am, "role")], "email": acc[col(am, "email")].str.lower(),
    })
    if col(am, "last_login"):
        accs["last_login"] = parse_dates(acc[col(am, "last_login")])
    else:
        accs["last_login"] = pd.NaT
        warnings.append("У файлі акаунтів не знайдено колонку з датою останнього входу — перевірку неактивності пропущено.")
    # дата реєстрації — необов'язкова: лише додається до знахідок і звіту, без попередження
    accs["created"] = parse_dates(acc[col(am, "created")]) if col(am, "created") else pd.NaT

    df = accs.merge(hrs.assign(_hr=True), on="email", how="left")
    df["matched"] = df["_hr"].eq(True)

    # --- Політика
    model = {_key(p): {_key(s): {_key(r) for r in roles} for s, roles in systems.items()}
             for p, systems in policy.get("role_model", {}).items()}
    admin_roles = {_key(r) for r in policy.get("admin_roles", [])}
    unknown_positions: set[str] = set()
    if not domain:
        warnings.append("Корпоративний домен не визначено — перевірку пошти пропущено.")

    findings: list[dict] = []
    for r in df.itertuples(index=False):
        def add(category, text, role=None, r=r):
            findings.append({
                "system": r.system, "login": r.login, "role": role if role is not None else r.role,
                "issue": text, "category": category,
                "email": None if pd.isna(r.email) else r.email,
                "employee": None if pd.isna(r.name) else r.name,
                "position": None if pd.isna(r.position) else r.position,
                "last_login": _date_str(r.last_login),
                "created": _date_str(r.created),
            })

        if domain and (pd.isna(r.email) or not str(r.email).endswith(domain)):
            add("bad_email", "не корпоративна або відсутня пошта")
        if not r.matched:
            add("no_hr", "акаунт без працівника в HR (спільний/технічний)")
        elif r.status == "terminated":
            add("terminated", "працівник звільнений")
        elif r.status == "leave":
            add("leave", "працівник у відпустці")
        if r.matched and pd.notna(r.position):
            allowed = model.get(_key(r.position))
            if allowed is None:
                unknown_positions.add(str(r.position))
            elif _key(r.role) not in allowed.get(_key(r.system), set()):
                add("role_mismatch", "роль не відповідає посаді")
        if pd.notna(r.role) and _key(r.role) in admin_roles:
            add("admin", "постійна admin-роль (має бути лише через PAM)")
        if pd.notna(r.last_login):
            days = (review_date - r.last_login).days
            if days > inactive_days:
                add("inactive", f"неактивний {days} днів")

    # --- Конфлікти ролей (SoD)
    for conflict in policy.get("sod_conflicts", []):
        need = {_key(x) for x in conflict["roles"]}
        sub = df[df["system"].map(_key) == _key(conflict["system"])]
        # Спершу відбираємо логіни, що мають усі ролі конфлікту (швидко, без групи на кожен логін),
        # і лише для них збираємо дані — інакше на тисячах акаунтів це займає секунди.
        role_keys = sub["role"].map(lambda x: _key(x) if pd.notna(x) else None)
        hit = role_keys.isin(need)
        counts = role_keys[hit].groupby(sub.loc[hit, "login"]).nunique()
        logins = counts[counts == len(need)].index
        for login, g in sub[sub["login"].isin(logins)].groupby("login"):
            first = lambda c: None if g[c].isna().all() else g[c].dropna().iloc[0]
            findings.append({
                "system": conflict["system"], "login": login,
                "role": "+".join(conflict["roles"]), "issue": conflict["reason"],
                "category": "sod", "email": first("email"), "employee": first("name"),
                "position": first("position"),
                "last_login": _date_str(g["last_login"].max()),  # найсвіжіший вхід серед ролей логіна
                "created": _date_str(g["created"].min()),        # найраніша реєстрація
            })

    if unknown_positions:
        warnings.append("Для цих посад немає правил, ролі не перевірялись: " +
                        ", ".join(sorted(unknown_positions)))

    res = pd.DataFrame(findings, columns=["system", "login", "role", "issue", "category",
                                          "email", "employee", "position", "last_login", "created"])
    res["severity"] = res["category"].map(SEVERITY)
    res["type"] = res["category"].map(CATEGORY_TITLE)
    return res, warnings, accs


# --------------------------------------------------------------------------
# Повний цикл: файли -> результат для API / CLI
# --------------------------------------------------------------------------
def _file_info(index, name, df, kind, mapping):
    fields = HR_FIELDS if kind == "hr" else ACC_FIELDS
    items = []
    for f in fields:
        m = mapping[f]
        sample = None
        if m["column"]:
            vals = df[m["column"]].dropna()
            sample = str(vals.iloc[0]) if len(vals) else None
        items.append({"key": f, "label": FIELD_LABELS[f], "required": f in REQUIRED[kind],
                      "column": m["column"], "score": m["score"],
                      "overridden": m["overridden"], "sample": sample})
    return {"index": index, "name": name, "kind": kind, "rows": int(len(df)),
            "columns": list(df.columns), "fields": items}


def run(files: list[tuple[str, bytes]], overrides: dict | None = None,
        review_date: str | None = None, inactive_days: int | None = None,
        domain: str | None = None, policy: dict | None = None,
        policy_text: str | None = None) -> dict:
    overrides = overrides or {}
    default_policy = load_policy()
    policy_error, policy_source = None, "default"
    if policy is not None:
        policy_source = "custom"
    elif policy_text and policy_text.strip():
        try:
            policy, policy_source = parse_policy_text(policy_text), "custom"
        except AnalysisError as e:
            policy_error = str(e)  # правила не застосовано — рахуємо за замовчуванням
    policy = policy or default_policy
    policy_meta = {
        "policy": policy, "policy_text": policy_to_text(policy),
        "policy_default_text": policy_to_text(default_policy),
        "policy_source": policy_source, "policy_error": policy_error,
    }
    if len(files) != 2:
        raise AnalysisError("Потрібно рівно 2 файли: вивантаження з HR і список акаунтів.")

    tables = [read_table(n, b) for n, b in files]
    roles = overrides.get("roles") or {}
    if {roles.get("hr"), roles.get("accounts")} == {0, 1}:
        hr_i, acc_i = roles["hr"], roles["accounts"]
    else:
        hr_i, acc_i = detect_kinds(tables)

    hr, acc = tables[hr_i], tables[acc_i]
    hm = build_mapping(hr, "hr", (overrides.get("columns") or {}).get("hr"))
    am = build_mapping(acc, "accounts", (overrides.get("columns") or {}).get("accounts"))
    info = {
        "hr": _file_info(hr_i, files[hr_i][0], hr, "hr", hm),
        "accounts": _file_info(acc_i, files[acc_i][0], acc, "accounts", am),
    }

    # параметри
    try:
        review = pd.Timestamp(review_date) if review_date else pd.Timestamp(date.today())
    except Exception as e:
        raise AnalysisError(f"Некоректна дата рев'ю: {review_date}") from e
    days = int(inactive_days) if inactive_days else int(policy.get("inactive_days", 90))
    detected_domain = detect_domain(hr[hm["email"]["column"]].str.lower()) if hm["email"]["column"] else ""
    dom = _norm_domain(domain) if domain is not None else detected_domain
    params = {"review_date": review.date().isoformat(), "inactive_days": days,
              "domain": dom, "domain_detected": detected_domain}

    # чи всі обов'язкові колонки знайдено
    errors = []
    for kind, mapping in (("hr", hm), ("accounts", am)):
        missing = [FIELD_LABELS[f] for f in REQUIRED[kind] if not mapping[f]["column"]]
        if missing:
            title = "HR-файлі" if kind == "hr" else "файлі акаунтів"
            errors.append(f"У {title} «{info[kind]['name']}» не вдалося знайти колонки: "
                          f"{', '.join(missing)}. Вкажіть їх вручну.")
    if errors:
        return {"ok": False, "errors": errors, "files": info, "params": params, **policy_meta}

    res, warnings, accs = analyze(hr, acc, hm, am, policy, review, days, dom)

    # --- підсумки
    key_pairs = accs[["system", "login"]].drop_duplicates()
    flagged = res[["system", "login"]].drop_duplicates()
    by_type = (res.groupby(["type", "severity"]).size().reset_index(name="count")
               .sort_values("count", ascending=False))
    by_system = res.groupby(["system", "severity"]).size().reset_index(name="count")
    top = (res.assign(score=res["severity"].map(SEVERITY_WEIGHT))
           .groupby(["system", "login"])
           .agg(findings=("issue", "size"), score=("score", "sum"),
                types=("type", lambda s: sorted(set(s))),
                employee=("employee", "first"), email=("email", "first"))
           .reset_index().sort_values(["score", "findings"], ascending=False).head(10))
    order = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    res = res.assign(_o=res["severity"].map(order)).sort_values(["_o", "system", "login"]).drop(columns="_o")

    clean = lambda d: json.loads(d.to_json(orient="records", force_ascii=False))
    return {
        "ok": True, "errors": [], "warnings": warnings, "files": info, "params": params,
        "summary": {
            "accounts_total": int(len(key_pairs)), "accounts_flagged": int(len(flagged)),
            "findings": int(len(res)),
            "critical": int((res["severity"] == "Критично").sum()),
            "by_type": clean(by_type), "by_system": clean(by_system),
        },
        "top_accounts": clean(top), "findings": clean(res),
        **policy_meta,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Access review: два CSV/XLSX (HR і акаунти, у будь-якому порядку).")
    ap.add_argument("files", nargs=2, metavar="FILE")
    ap.add_argument("--date", help="дата рев'ю, РРРР-ММ-ДД (за замовчуванням сьогодні)")
    ap.add_argument("--inactive-days", type=int)
    ap.add_argument("--domain", help="корпоративний домен (за замовчуванням визначається з HR)")
    ap.add_argument("-o", "--out", help="куди записати звіт (за замовчуванням у консоль)")
    ap.add_argument("--policy", help="файл із правилами (текст або JSON); за замовчуванням policy.json")
    a = ap.parse_args(argv)

    try:
        files = [(Path(p).name, Path(p).read_bytes()) for p in a.files]
        policy = parse_policy_text(Path(a.policy).read_text(encoding="utf-8-sig")) if a.policy else None
        res = run(files, review_date=a.date, inactive_days=a.inactive_days, domain=a.domain,
                  policy=policy)
    except (AnalysisError, OSError) as e:
        print(f"Помилка: {e}", file=sys.stderr)
        return 1
    if not res["ok"]:
        print("\n".join(res["errors"]), file=sys.stderr)
        return 1

    for kind, title in (("hr", "HR"), ("accounts", "Акаунти")):
        f = res["files"][kind]
        cols = ", ".join(f"{x['key']}={x['column']}" for x in f["fields"] if x["column"])
        print(f"{title}: {f['name']} ({f['rows']} рядків) → {cols}", file=sys.stderr)
    for w in res["warnings"]:
        print(f"Увага: {w}", file=sys.stderr)

    report = pd.DataFrame(res["findings"], columns=["system", "login", "email", "role", "issue"])
    if a.out:
        report.to_csv(a.out, index=False, encoding="utf-8-sig")
        print(f"Знахідок: {len(report)}. Звіт: {a.out}", file=sys.stderr)
    else:
        report.to_csv(sys.stdout, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
