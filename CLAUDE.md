# CLAUDE.md — 行銷年度行事曆專案工作指引

> 優先級高於全域設定。`.claude.md` 是本檔的同步複本，兩檔內容必須一致。

---

## 專案背景

台灣行銷人員用的 **2026 行銷年度行事曆** 靜態網站，對標 atmarketing.tw/2026calendar/。
功能規格見 `SDD.md`（既有功能）與 `SDD-v3.md`（F1–F5 內部團隊版功能）。

---

## 架構

| 類型 | 路徑 | 說明 |
|------|------|------|
| 前端 | `index.html` | CSS、JS、HTML 全部內嵌；單檔部署 |
| 自動化 | `scripts/weekly_digest.py` | 週報 bot（三檔例外） |
| CI/CD | `.github/workflows/weekly-digest.yml` | GitHub Actions（三檔例外） |
| 本地伺服器 | `python3 -m http.server 8181` | 備用；`server.py` 補 UTF-8 charset |

**前端維持單一 `index.html`**，不新增 `.js` / `.css` 分離檔案，不引入前端框架。
`scripts/` 與 `.github/workflows/` 是已知例外（後端自動化，非前端）。

---

## 資料層

### APP_STATE（單一資料來源）

```js
const APP_STATE = {
  view: 'card',                          // card | list | holiday | print
  categories: new Set(['tw','ec','local','intl','life']),
  industry: 'all',
  search: '',
  expanded: new Set(),
  events:   [...FALLBACK_EVENTS],
  holidays: [...FALLBACK_HOLIDAYS],
  cpm:      { ...FALLBACK_CPM },
};
```

### 事件欄位

```js
{
  id: 'tw_0101',       // 唯一 ID
  month: 1,            // 1-12
  day: 1,
  name: '元旦',
  cat: 'tw',           // tw | ec | local | intl | life
  priority: 2,         // 1-3（3 最高）
  industry: ['all'],   // all | food | beauty | tech | travel | fashion | edu | retail
  leadWeeks: 1,        // 建議提前準備週數（0 = 無）
  topics: ['新年新氣象'],
  channel: ['Meta', 'Google關鍵字'],
}
```

Google Sheets 多值欄位（industry / topics / channel）以 `|` 分隔；
`fetchSheetData(gid)` 讀取 CSV，`loadSheetData()` 負責錯誤處理與 Fallback。

### localStorage keys（前綴 `cal_`）

| key | 值 |
|-----|----|
| `cal_theme` | `dark` \| `light` |
| `cal_categories` | JSON 陣列 |
| `cal_industry` | 產業代碼字串 |
| `cal_view` | `card` \| `list` \| `holiday` \| `print` |
| `cal_expanded` | JSON 陣列 |

---

## 渲染函式（index.html `<script>` 區）

| 函式 | 說明 |
|------|------|
| `renderCards()` | 月份卡片視圖（視圖 A） |
| `renderList()` | 行銷規劃列表（視圖 B） |
| `renderHoliday()` | 假日 & 節氣（視圖 C） |
| `renderPrint()` | 列印視圖（視圖 D）；跟隨 filterEvents() |
| `renderCountdown()` | 倒數橫幅（含 CPM 徽章、Lead Time） |
| `renderQuarterOverview()` | Q1–Q4 季度概覽面板（視圖 A 頂部） |
| `renderMonthNav()` | 月份導航列 |
| `filterEvents()` | 類別 × 產業 × 搜尋 AND 交集，回傳陣列 |
| `switchView(view)` | 切換視圖並儲存狀態 |
| `refreshView()` | 篩選變更時重繪當前視圖 |
| `exportICS()` | 產生 .ics 並觸發下載 |
| `saveState()` / `loadState()` | localStorage 封裝 |

---

## CSS 規範

### 必須用 CSS Custom Properties
禁止 hardcode hex 值，以下為已知例外：
- active 按鈕文字色 `#fff` / `#1a1a1a`（對比需求）
- 列印樣式 `#ccc` 邊框（`@media print` 強制色）

### 類別顏色（不可更改）
`--color-tw` 台灣節慶 / `--color-ec` 電商檔期 / `--color-local` 在地活動 /
`--color-intl` 國際日 / `--color-life` 生活節氣

### CPM 顏色（v3 新增）
`--cpm-high-bg` / `--cpm-high-txt` / `--cpm-med-bg` / `--cpm-med-txt`

### v3 新增 CSS class
`.cpm-badge`（high / medium / extreme 徽章）、`.cpm-month-alert`（整月警示列）、
`.lead-hint` / `.lead-hint.urgent`（準備提醒）、
`.quarter-panel`（季度概覽）、`.print-table`（列印表格）

---

## PR 與分支規範

每個變更都走完整流程，**禁止直接 push main**：

1. 開 GitHub Issue
2. 從 `main` 建分支：`task/<issue#>-<kebab-description>`
3. 開 PR → merge → 刪除分支

Commit 格式：conventional commits，末尾加：
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

---

## 禁止事項

- ❌ 不引入前端框架（React / Vue / Angular）
- ❌ 不用 `document.write()`
- ❌ 不 hardcode 顏色（必須用 CSS 變數，例外見上）
- ❌ 不把 UI 邏輯混入資料陣列
- ❌ 不在 `index.html` 外新增 `.js` / `.css` 前端檔案

---

## 週報 bot（scripts/）

`scripts/weekly_digest.py`：Python 3 標準函式庫（零第三方依賴）。
- 優先讀 Google Sheets CSV；失敗時解析 `index.html` 內 FALLBACK 常數作備援
- 環境變數：`DIGEST_WEBHOOK_URL`（必填）、`DIGEST_PLATFORM`（slack/line）、`LINE_CHANNEL_ID`
- `SITE_URL` 可覆蓋預設網站連結

---

## 本地預覽

```bash
# 推薦（port 8181 避免與其他服務衝突）
python3 -m http.server 8181

# 若有 server.py（補 UTF-8 charset）
python3 server.py
```

不建議 `open index.html`：Google Sheets fetch 在 `file://` 下行為與正式環境不一致。

---

## 重要資料備忘

### 2026 國定假日（依人事行政局 CSV）
| 假日 | 日期 | 補假 | 連假 |
|------|------|------|------|
| 元旦 | 1/1 (四) | — | 1天 |
| 農曆春節 | 2/15–2/20 | 2/20 (五) | 9天 (2/14–2/22) |
| 和平紀念日 | 2/28 (六) | 2/27 (五) | 3天 |
| 兒童節+清明節 | 4/4–4/5 | 4/3、4/6 | 4天 |
| 勞動節 | 5/1 (五) | — | 3天 |
| 端午節 | 6/19 (五) | — | 3天 |
| 中秋節 | 9/25 (五) | — | 4天 (含教師節) |
| 國慶日 | 10/10 (六) | 10/9 (五) | 3天 |
| 臺灣光復節 | 10/25 (日) | 10/26 (一) | 3天 |
| 行憲紀念日 | 12/25 (五) | — | 3天 |

### 2026 年 24 節氣
小寒 1/5、大寒 1/20、立春 2/4、雨水 2/19、驚蟄 3/6、春分 3/20、
清明 4/5、穀雨 4/20、立夏 5/6、小滿 5/21、芒種 6/7、夏至 6/21、
小暑 7/7、大暑 7/23、立秋 8/7、處暑 8/23、白露 9/8、秋分 9/23、
寒露 10/8、霜降 10/23、立冬 11/7、小雪 11/22、大雪 12/7、冬至 12/22

### 建議渠道（固定 9 種，不可新增）
Google關鍵字、Google Banner、Youtube、Meta、LINE、CRM-EDM、CRM-簡訊、Taboola、Dcard
