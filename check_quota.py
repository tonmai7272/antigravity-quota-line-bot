#!/usr/bin/env python3
"""
Daily Antigravity / Gemini (Google AI Pro) quota checker & LINE push notifier.
Formats detailed per-model usage in Thai (Asia/Bangkok time).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

BKK_TZ = timezone(timedelta(hours=7))

THAI_WEEKDAYS = ["จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส.", "อา."]
THAI_MONTHS = [
    "",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
]


def format_bkk_datetime(dt: datetime) -> str:
    """Format datetime as '<ว. d MMM HH:mm>' in Asia/Bangkok time."""
    bkk = dt.astimezone(BKK_TZ)
    wd = THAI_WEEKDAYS[bkk.weekday()]
    month = THAI_MONTHS[bkk.month]
    return f"{wd} {bkk.day} {month} {bkk.strftime('%H:%M')}"


def parse_iso_datetime(val: str) -> datetime:
    """Parse ISO-8601 timestamp or epoch seconds into a timezone-aware datetime."""
    val = str(val).strip()
    if val.isdigit():
        return datetime.fromtimestamp(int(val), tz=timezone.utc)
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"
    dt = datetime.fromisoformat(val)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BKK_TZ)
    return dt


def format_pct(val: float, detailed: bool = False) -> str:
    """Format percentage nicely."""
    if not detailed and abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:.1f}"


def format_remaining_short(reset_dt: datetime, now: datetime) -> str:
    rem_sec = max(0.0, (reset_dt - now).total_seconds())
    days = int(rem_sec // 86400)
    hours = int((rem_sec % 86400) // 3600)
    mins = int((rem_sec % 3600) // 60)
    if days > 0:
        return f"เหลือ {days} วัน {hours} ชม."
    if hours > 0:
        return f"เหลือ {hours} ชม. {mins} นาที"
    return f"เหลือ {mins} นาที"


def summarize_model_groups(entries: list[dict], group_defs: list[tuple[str, tuple[str, ...]]]) -> list[tuple[str, float]]:
    """Group model variants into readable summary rows with their max used_percent."""
    results = []
    for display_name, prefixes in group_defs:
        matched = [
            e["used_percent"]
            for e in entries
            if any(p.lower() in e.get("label", "").lower() for p in prefixes)
        ]
        if matched:
            results.append((display_name, max(matched)))
    return results


def build_success_message(
    email: str,
    weekly_used: float,
    weekly_reset: datetime,
    five_hour_used: float | None = None,
    five_hour_reset: datetime | None = None,
    plan_name: str | None = None,
    five_hour_models: list[dict] | None = None,
    weekly_models: list[dict] | None = None,
    updated_at: datetime | None = None,
    now: datetime | None = None,
) -> str:
    if now is None:
        now = datetime.now(BKK_TZ)

    header_plan = f" ({plan_name})" if plan_name else ""
    lines = [f"☀️ Gemini{header_plan} · {email}"]

    if five_hour_used is not None and five_hour_reset is not None:
        rem_5h = format_remaining_short(five_hour_reset, now)
        lines.append(
            f"• ลิมิต 5 ชั่วโมง: {format_pct(five_hour_used)}% (รีเซ็ต {format_bkk_datetime(five_hour_reset)} · {rem_5h})"
        )
        if five_hour_models:
            groups_5h = summarize_model_groups(
                five_hour_models,
                [
                    ("Gemini 4 Neon / Hydrogen", ("Neon", "Hydrogen")),
                    ("Gemini 3.8 Flash", ("Flash",)),
                    ("Claude 5.5 Opus / Sonnet", ("Claude",)),
                    ("GPT-OSS 120B", ("GPT-OSS",)),
                ],
            )
            for idx, (g_name, g_used) in enumerate(groups_5h):
                branch = "└─" if idx == len(groups_5h) - 1 else "├─"
                rem_pct = max(0.0, 100.0 - g_used)
                lines.append(
                    f"  {branch} {g_name}: ใช้ไป {format_pct(g_used, True)}% (เหลือ {format_pct(rem_pct, True)}%)"
                )

    rem_wk_str = format_remaining_short(weekly_reset, now)
    lines.append(
        f"• ลิมิตรายสัปดาห์: {format_pct(weekly_used)}% (รีเซ็ต {format_bkk_datetime(weekly_reset)} · {rem_wk_str})"
    )
    if weekly_models:
        groups_wk = summarize_model_groups(
            weekly_models,
            [
                ("Gemini 4 Argon", ("Gemini 4 Argon",)),
                ("Orchestrator (Argon)", ("Orchestrator (Argon)",)),
            ],
        )
        for idx, (g_name, g_used) in enumerate(groups_wk):
            branch = "└─" if idx == len(groups_wk) - 1 else "├─"
            rem_pct = max(0.0, 100.0 - g_used)
            lines.append(
                f"  {branch} {g_name}: ใช้ไป {format_pct(g_used, True)}% (เหลือ {format_pct(rem_pct, True)}%)"
            )

    rem_seconds = max(0.0, (weekly_reset - now).total_seconds())
    rem_hours_total = rem_seconds / 3600.0
    days = int(rem_seconds // 86400)
    hours = int((rem_seconds % 86400) // 3600)

    if rem_hours_total <= 72.0 and weekly_used < 50.0:
        lines.append(
            f"⚠️ ลิมิตรายสัปดาห์ ใช้ไป {format_pct(weekly_used)}% เหลือ {days} วัน {hours} ชม. ก่อนรีเซ็ต — ใช้ให้คุ้ม"
        )
    elif weekly_used >= 90.0:
        lines.append(
            f"🔴 ลิมิตรายสัปดาห์ ใช้ไป {format_pct(weekly_used)}% ใกล้เต็ม"
        )
    else:
        lines.append("✅ ปกติ")

    if updated_at is not None:
        lines.append(f"🕒 ซิงก์ล่าสุด: {format_bkk_datetime(updated_at)}")

    return "\n".join(lines)


def build_error_message(email: str, reason: str) -> str:
    return f"❗ Gemini · {email}\nดึงข้อมูลการใช้งานไม่ได้วันนี้ ({reason})"


def normalize_quota_payload(data: dict) -> dict:
    email = data.get("email") or os.environ.get("ACCOUNT_EMAIL") or "tonmai7272@gmail.com"
    ref_now = datetime.now(timezone.utc)
    updated_dt = None
    if "updated_at" in data:
        try:
            updated_dt = parse_iso_datetime(data["updated_at"])
            ref_now = updated_dt
        except Exception:
            pass

    user_status = data.get("userStatus") or data
    plan_name = (
        user_status.get("planName")
        or user_status.get("planStatus", {}).get("planInfo", {}).get("planName")
        or "Pro"
    )

    if "cascadeModelConfigData" in user_status:
        configs = user_status["cascadeModelConfigData"].get("clientModelConfigs", [])
        five_hour_candidates = []
        weekly_candidates = []

        for cfg in configs:
            quota = cfg.get("quotaInfo") or {}
            if "remainingFraction" not in quota or "resetTime" not in quota:
                continue
            rem = float(quota["remainingFraction"])
            used = round(max(0.0, (1.0 - rem) * 100.0), 1)
            reset_str = quota["resetTime"]
            reset_dt = parse_iso_datetime(reset_str)
            hours_ahead = (reset_dt - ref_now).total_seconds() / 3600.0

            entry = {
                "label": cfg.get("label", ""),
                "used_percent": used,
                "reset_at": reset_str,
                "reset_dt": reset_dt,
            }
            if hours_ahead <= 12.0:
                five_hour_candidates.append(entry)
            else:
                weekly_candidates.append(entry)

        best_5h = None
        if five_hour_candidates:
            best_5h = max(five_hour_candidates, key=lambda x: x["used_percent"])

        best_weekly = None
        if weekly_candidates:
            best_weekly = max(weekly_candidates, key=lambda x: x["used_percent"])
        elif best_5h:
            best_weekly = best_5h
            best_5h = None

        if best_weekly:
            return {
                "email": user_status.get("email") or email,
                "plan_name": plan_name,
                "updated_at": updated_dt,
                "five_hour": (
                    {"used_percent": best_5h["used_percent"], "reset_at": best_5h["reset_at"]}
                    if best_5h
                    else None
                ),
                "weekly": {
                    "used_percent": best_weekly["used_percent"],
                    "reset_at": best_weekly["reset_at"],
                },
                "five_hour_models": five_hour_candidates,
                "weekly_models": weekly_candidates,
            }

    if isinstance(data.get("models"), list) and data["models"]:
        models = data["models"]
        most_used = max(
            models,
            key=lambda m: float(
                (m.get("weekly") or {}).get("used_percent")
                or (m.get("five_hour") or {}).get("used_percent")
                or 0.0
            ),
        )
        return {
            "email": data.get("email") or email,
            "plan_name": plan_name,
            "updated_at": updated_dt,
            "five_hour": most_used.get("five_hour"),
            "weekly": most_used.get("weekly"),
            "five_hour_models": None,
            "weekly_models": None,
        }

    if "weekly" in data:
        return {
            "email": email,
            "plan_name": plan_name,
            "updated_at": updated_dt,
            "five_hour": data.get("five_hour"),
            "weekly": data.get("weekly"),
            "five_hour_models": None,
            "weekly_models": None,
        }

    raise ValueError("รูปแบบ JSON ไม่มีฟิลด์ weekly หรือ cascadeModelConfigData ที่รองรับ")


def fetch_quota_data() -> dict:
    raw_json = os.environ.get("QUOTA_JSON_DATA", "").strip()
    if raw_json:
        return normalize_quota_payload(json.loads(raw_json))

    quota_file = os.environ.get("QUOTA_JSON_FILE", "quota_state.json")
    if os.path.isfile(quota_file):
        with open(quota_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return normalize_quota_payload(json.loads(content))

    api_url = os.environ.get("QUOTA_API_URL", "").strip()
    if api_url:
        headers = {"Accept": "application/json"}
        api_token = os.environ.get("QUOTA_API_TOKEN", "").strip()
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return normalize_quota_payload(json.loads(body))

    raise RuntimeError(
        "ยังไม่มีข้อมูลโควตาจาก Antigravity IDE (กรุณาซิงก์ quota_state.json)"
    )


def send_line_push(token: str, user_id: str, message: str) -> None:
    url = "https://api.line.me/v2/bot/message/push"
    payload = json.dumps(
        {
            "to": user_id,
            "messages": [{"type": "text", "text": message}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"LINE push sent successfully (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"LINE API error (HTTP {e.code}): {err_body}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    token = os.environ.get("LINE_CHANNEL_TOKEN", "").strip()
    user_id = os.environ.get("LINE_USER_ID", "").strip()
    email = os.environ.get("ACCOUNT_EMAIL", "").strip() or "tonmai7272@gmail.com"

    if not token or not user_id:
        print("ERROR: LINE_CHANNEL_TOKEN and LINE_USER_ID must be set.", file=sys.stderr)
        sys.exit(1)

    try:
        quota = fetch_quota_data()
        acct_email = quota.get("email") or email
        weekly = quota.get("weekly")
        if not weekly or "used_percent" not in weekly or "reset_at" not in weekly:
            raise ValueError("ข้อมูลลิมิตรายสัปดาห์ไม่ครบ (ต้องมี used_percent และ reset_at)")

        w_used = float(weekly["used_percent"])
        w_reset = parse_iso_datetime(str(weekly["reset_at"]))

        fh = quota.get("five_hour")
        fh_used = None
        fh_reset = None
        if fh and "used_percent" in fh and "reset_at" in fh and fh["reset_at"]:
            fh_used = float(fh["used_percent"])
            fh_reset = parse_iso_datetime(str(fh["reset_at"]))

        message = build_success_message(
            email=acct_email,
            weekly_used=w_used,
            weekly_reset=w_reset,
            five_hour_used=fh_used,
            five_hour_reset=fh_reset,
            plan_name=quota.get("plan_name"),
            five_hour_models=quota.get("five_hour_models"),
            weekly_models=quota.get("weekly_models"),
            updated_at=quota.get("updated_at"),
        )
    except Exception as exc:
        message = build_error_message(email=email, reason=str(exc))

    print("--- Message to send ---")
    print(message)
    print("-----------------------")
    send_line_push(token=token, user_id=user_id, message=message)


if __name__ == "__main__":
    main()
