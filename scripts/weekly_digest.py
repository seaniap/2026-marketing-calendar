#!/usr/bin/env python3
"""
2026 行銷年度行事曆 — 週報 bot
每週一 09:00 Asia/Taipei 推送近期行銷檔期摘要至團隊頻道。

環境變數：
  DIGEST_WEBHOOK_URL  必填；Slack Incoming Webhook URL 或 LINE Channel Access Token
  DIGEST_PLATFORM     選填；slack（預設）| line
  LINE_CHANNEL_ID     LINE 模式必填；目標 group/user ID
  SITE_URL            選填；網站連結（預設 GitHub repo 頁面）
"""
import ast, csv, io, json, os, re, sys, urllib.request, urllib.error
from datetime import date, timedelta

# ── 設定 ────────────────────────────────────────────────────────
PUBLISHED_ID = "2PACX-1vQ_tAy2LdCTeOk7rkuzMqgOv-omJRT21oFiGFG9WffDtpepkIM0ubsPr1ILwduSby-Gbn1uSaxu_zSn"
GID_EVENTS   = "0"
GID_CPM      = "742683031"
SITE_URL     = os.environ.get(
    "SITE_URL",
    "https://seaniap.github.io/2026-marketing-calendar/"
)

CAT_EMOJI = {"tw": "🇹🇼", "ec": "🛒", "local": "📍", "intl": "🌍", "life": "📚"}

# ── index.html Fallback 解析 ─────────────────────────────────────
def _extract_block(text, var_name, open_ch, close_ch):
    """從 JS 原始碼中提取指定常數的完整括號區塊。"""
    start = text.find(f"const {var_name}")
    if start == -1:
        raise ValueError(f"{var_name} not found in index.html")
    open_pos = text.index(open_ch, start)
    depth = 0
    for i, ch in enumerate(text[open_pos:]):
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[open_pos : open_pos + i + 1]
    raise ValueError(f"Unmatched bracket for {var_name}")


def _js_to_py(s):
    """最小化 JS 物件字面量 → Python 字面量轉換。"""
    s = re.sub(r"//[^\n]*", "", s)                           # 移除行注釋
    s = re.sub(r"(\{|,)\s*([a-zA-Z_]\w*)\s*:", r"\1'\2':", s)  # 引用 key
    s = re.sub(r",(\s*[}\]])", r"\1", s)                     # 移除 trailing comma
    return s


def load_fallback(html_path):
    """從 index.html 解析 FALLBACK_EVENTS / FALLBACK_CPM。"""
    try:
        text = open(html_path, encoding="utf-8").read()

        events_js = _extract_block(text, "FALLBACK_EVENTS", "[", "]")
        raw_events = ast.literal_eval(_js_to_py(events_js))
        events = [
            {
                "id":        str(e.get("id", "")),
                "month":     int(e.get("month", 0)),
                "day":       int(e.get("day", 0)),
                "name":      str(e.get("name", "")),
                "cat":       str(e.get("cat", "")),
                "priority":  int(e.get("priority", 1)),
                "leadWeeks": int(e.get("leadWeeks", 0)),
            }
            for e in raw_events
            if int(e.get("month", 0)) > 0
        ]

        cpm_js = _extract_block(text, "FALLBACK_CPM", "{", "}")
        raw_cpm = ast.literal_eval(_js_to_py(cpm_js))
        cpm = {int(k): {"level": v["level"], "msg": v["msg"]} for k, v in raw_cpm.items()}

        return events, cpm

    except Exception as exc:
        print(f"⚠️  Fallback 解析失敗：{exc}", file=sys.stderr)
        return [], {}


# ── Google Sheets CSV 載入 ───────────────────────────────────────
def _fetch_csv(gid):
    url = (
        f"https://docs.google.com/spreadsheets/d/e/{PUBLISHED_ID}"
        f"/pub?gid={gid}&single=true&output=csv"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "marketing-calendar-bot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def load_sheets_events():
    rows = list(csv.DictReader(io.StringIO(_fetch_csv(GID_EVENTS))))
    if not rows:
        raise ValueError("Empty events sheet")
    events = []
    for r in rows:
        try:
            events.append({
                "id":        (r.get("id") or "").strip(),
                "month":     int(r.get("month") or 0),
                "day":       int(r.get("day") or 0),
                "name":      (r.get("name") or "").strip(),
                "cat":       (r.get("cat") or "").strip(),
                "priority":  int(r.get("priority") or 1),
                "leadWeeks": int(r.get("leadWeeks") or 0),
            })
        except (ValueError, KeyError):
            continue
    return [e for e in events if e["month"] > 0]


def load_sheets_cpm():
    rows = list(csv.DictReader(io.StringIO(_fetch_csv(GID_CPM))))
    cpm = {}
    for r in rows:
        try:
            m = int(r.get("month") or 0)
            if 1 <= m <= 12:
                cpm[m] = {"level": (r.get("level") or "normal").strip(),
                           "msg":   (r.get("msg") or "").strip()}
        except (ValueError, KeyError):
            continue
    return cpm


# ── 訊息組裝 ────────────────────────────────────────────────────
def build_message(events, cpm, today=None):
    if today is None:
        today = date.today()

    mon = today - timedelta(days=today.weekday())   # 本週一
    sun = mon + timedelta(days=6)                   # 本週日
    in4w = today + timedelta(weeks=4)

    lines = [
        "*📅 2026 行銷週報*",
        f"本週：{mon.strftime('%m/%d')}（一）～ {sun.strftime('%m/%d')}（日）",
        "",
    ]

    # ① 未來 4 週檔期
    upcoming = sorted(
        [
            (date(2026, e["month"], e["day"]), e)
            for e in events
            if today <= date(2026, e["month"], e["day"]) <= in4w
            and (e["priority"] >= 2 or e["cat"] in ("tw", "ec"))
        ],
        key=lambda x: x[0],
    )
    lines.append("📅 *未來 4 週行銷檔期*")
    if upcoming:
        for ed, e in upcoming:
            emoji = CAT_EMOJI.get(e["cat"], "📌")
            prio  = "🔥" * min(e["priority"], 3)
            lines.append(f"  {ed.strftime('%m/%d')} {emoji} {e['name']} {prio}")
    else:
        lines.append("  本週起 4 週內無重要行銷檔期")
    lines.append("")

    # ② 本週該開始準備
    prep_this_week = sorted(
        [
            (date(2026, e["month"], e["day"]) - timedelta(weeks=e["leadWeeks"]),
             e,
             date(2026, e["month"], e["day"]))
            for e in events
            if e["priority"] >= 2 and e["leadWeeks"] > 0
            and mon <= date(2026, e["month"], e["day"]) - timedelta(weeks=e["leadWeeks"]) <= sun
        ],
        key=lambda x: x[0],
    )
    lines.append("🔔 *本週該開始準備*")
    if prep_this_week:
        for pd, e, ed in prep_this_week:
            lines.append(
                f"  {pd.strftime('%m/%d')} 開始準備｜"
                f"{e['name']}（{ed.strftime('%m/%d')}，提前 {e['leadWeeks']} 週）"
            )
    else:
        lines.append("  本週無需啟動準備事項")
    lines.append("")

    # ③ 本月 CPM 警示（normal 省略）
    cur_cpm = cpm.get(today.month)
    if cur_cpm and cur_cpm.get("level", "normal") != "normal":
        lines.append("⚡ *本月 CPM 警示*")
        lines.append(f"  {cur_cpm['msg']}")
        lines.append("")

    lines.append(f"🔗 {SITE_URL}")
    return "\n".join(lines)


# ── Webhook 推送 ─────────────────────────────────────────────────
def _http_post(url, payload_bytes, headers):
    req = urllib.request.Request(url, data=payload_bytes, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def send_slack(webhook_url, text):
    payload = json.dumps({"text": text}).encode("utf-8")
    _http_post(webhook_url, payload, {"Content-Type": "application/json"})


def send_line(channel_token, text, channel_id):
    payload = json.dumps({
        "to": channel_id,
        "messages": [{"type": "text", "text": text}],
    }).encode("utf-8")
    _http_post(
        "https://api.line.me/v2/bot/message/push",
        payload,
        {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {channel_token}",
        },
    )


def send(text):
    platform    = os.environ.get("DIGEST_PLATFORM", "slack").lower()
    webhook_url = os.environ.get("DIGEST_WEBHOOK_URL", "")
    if not webhook_url:
        raise RuntimeError("DIGEST_WEBHOOK_URL 環境變數未設定")

    if platform == "line":
        channel_id = os.environ.get("LINE_CHANNEL_ID", "")
        if not channel_id:
            raise RuntimeError("LINE 模式需要 LINE_CHANNEL_ID 環境變數")
        send_line(webhook_url, text, channel_id)
        print("✅ LINE 週報推送成功", file=sys.stderr)
    else:
        send_slack(webhook_url, text)
        print("✅ Slack 週報推送成功", file=sys.stderr)


# ── 主程式 ──────────────────────────────────────────────────────
def main():
    html_path = os.path.join(os.path.dirname(__file__), "..", "index.html")

    # 優先 Google Sheets；失敗回退 Fallback
    try:
        events = load_sheets_events()
        cpm    = load_sheets_cpm()
        print(f"✅ Google Sheets 載入成功：{len(events)} 個事件", file=sys.stderr)
    except Exception as exc:
        print(f"⚠️  Google Sheets 失敗：{exc}，改用 Fallback", file=sys.stderr)
        events, cpm = load_fallback(html_path)
        if not events:
            print("❌ Fallback 亦失敗，中止", file=sys.stderr)
            sys.exit(1)
        print(f"✅ Fallback 載入：{len(events)} 個事件", file=sys.stderr)

    msg = build_message(events, cpm)
    print("── 訊息預覽 ──────────────────", file=sys.stderr)
    print(msg, file=sys.stderr)
    print("──────────────────────────────", file=sys.stderr)

    send(msg)


if __name__ == "__main__":
    main()
