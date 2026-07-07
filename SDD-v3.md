# SDD v3 — 2026 行銷年度行事曆「內部團隊版」擴充規格

> 版本：v3.0 | 日期：2026-07-08 | 作者：seanyeh
> 本文件為 `SDD.md`（v2.0）的擴充，只描述新增功能；既有功能規格仍以 `SDD.md` 為準。
> 決策脈絡見 `ideas/2026-calendar-roadmap.md` 與 `ideas/feature-gap-analysis.md`。

---

## 1. 定位與範圍

### 1.1 產品定位（v3 的核心轉變）

| | v2（現況） | v3（本規格） |
|---|---|---|
| 定位 | 對外公開的查閱型行事曆 | **內部團隊的行銷規劃工具** |
| 使用者 | 不特定行銷人員 | 公司內部團隊成員 |
| 價值 | 查閱台灣節日 / 檔期 | 查閱 + **餵進既有工作流程**（Google Calendar、團隊頻道） |

核心策略：**不當另一個日曆，當餵進既有日曆的資料源。**
提醒機制交給 Google Calendar（透過 .ics 匯出）與團隊即時通訊頻道（透過週報 bot），本產品不自建任何提醒基礎設施。

### 1.2 功能總覽（依開發優先序）

| 編號 | 功能 | 優先 | 說明 |
|------|------|------|------|
| F1 | Q1–Q4 季度概覽面板 | P1 | 一眼掌握全年重點分布 |
| F2 | 倒數橫幅整合 CPM 警示 + Lead Time | P2 | 資料已備齊，實用性最高 |
| F3 | 列印視圖（第 4 個 tab） | P3 | 提案簡報 / 紙本規劃用 |
| F4 | .ics 匯出（匯入 Google Calendar） | P4 | 提醒機制的正解，取代自建推播 |
| F5 | 週報 bot（每週推送近期檔期到團隊頻道） | P5 | 唯一的「主動提醒」，用排程 + webhook 實現 |

### 1.3 明確不做（Out of Scope）

| 項目 | 不做的理由 |
|------|-----------|
| 帳號系統 / 多用戶工作區 | 內部信任環境不需要；多版本需求用 Google Sheets 多分頁解決 |
| 自建推播 / Email 提醒服務 | Commodity 基礎設施，F4 + F5 已覆蓋提醒需求 |
| 分享按鈕 | 對外功能，內部無意義 |
| React 重構 | 目前功能量級 Vanilla JS 足夠，重構無對應收益 |
| Python 常駐後端（FastAPI / Railway） | F5 用 GitHub Actions 排程即可，不需常駐服務 |
| 行銷議題 AI 類別（第 6 類） | 需要內容生成能力，留待未來評估 |
| 對外 SaaS 化 / 付費功能 | 定位為內部工具 |

若未來要重啟上述任一項，先回到 `ideas/2026-calendar-roadmap.md` 重新評估，不直接動工。

### 1.4 技術約束

- **網站前端維持三檔架構**（`index.html` + `style.css` + `script.js`），F1–F4 全部在既有三檔內實作，不新增前端檔案、不引入函式庫。
- **F5 是獨立的自動化腳本**，不屬於網站前端：新增 `scripts/weekly_digest.py` 與 `.github/workflows/weekly-digest.yml`。此為三檔規則的既定例外（比照 `server.py`），需同步更新 `CLAUDE.md` 的禁止事項說明（見里程碑 M6）。
- 所有新功能只讀 `APP_STATE`，不新增資料來源；季度統計等衍生資料一律在渲染時計算，不落地儲存。
- 新增顏色一律使用 CSS Custom Properties（沿用既有例外規則）。

---

## 2. 功能規格

### F1 — Q1–Q4 季度概覽面板

**位置**：卡片視圖（view-card）頂部、倒數橫幅之下；僅卡片視圖顯示。

**版面**：4 欄 Grid（RWD：`>=768px` 4 欄、`<768px` 2 欄 × 2 列）。

**每季面板內容**（全部由 `APP_STATE` 衍生計算，不新增資料）：

| 區塊 | 計算規則 |
|------|---------|
| 季度標題 | `Q1 (1–3月)` … `Q4 (10–12月)` |
| 火焰熱度 | 取該季 3 個月中 CPM level 最高者：`extreme`→🔥🔥🔥、`high`→🔥🔥、`medium`→🔥、`normal`→不顯示 |
| 重點事件 | 該季事件依 `priority` 降冪、日期升冪排序，取前 4 筆，顯示 `日期 + 名稱 + 類別色點` |
| 議題標籤 | 彙整該季 `priority >= 2` 事件的 `topics`，去重後取前 5 個，顯示為 `#標籤` |

**互動**：
- 點擊季度面板 → 平滑捲動至該季第一個月的月份卡片。
- 面板內容**跟隨目前篩選結果**（類別 × 產業 × 搜尋的交集）；篩選後該季無事件時顯示空狀態文字「本季無符合事件」。

**實作備註**：新增 `renderQuarterOverview()`，於篩選變更時與 `renderCards()` 一同重繪；資料計算不操作 DOM。

### F2 — 倒數橫幅整合 CPM 警示 + Lead Time

**現況**：倒數橫幅顯示最近 3 個 `priority === 3` 檔期的倒數天數。

**擴充**（每個倒數項目新增兩項資訊）：

1. **CPM 徽章**：顯示該事件所屬月份的 CPM level 徽章（沿用 `--cpm-*` 變數與 §SDD.md 3.5 的等級定義），`normal` 不顯示徽章。
2. **準備提醒**：以 `準備開始日 = 事件日期 − leadWeeks × 7 天` 計算：
   - 今天早於準備開始日 → 顯示「📋 N 天後開始準備」
   - 今天已達準備開始日 → 顯示「⚠️ 已進入準備期（建議提前 X 週）」，樣式加強（橙色）

**新增整月警示列**：若「當前月份」的 CPM level 為 `high` 或 `extreme`，倒數橫幅頂部加一行整幅警示（顯示該月 `CPM_ALERTS.msg`），讓旺季期間打開頁面第一眼就看到。

**實作備註**：擴充 `renderCountdown()`；CPM 資料讀 `APP_STATE.cpm`，無新資料需求。

### F3 — 列印視圖（第 4 個視圖 tab）

**入口**：視圖切換列新增第 4 個 tab「🖨 列印」；`cal_view` localStorage 值新增 `print`。

**畫面內容**（螢幕上先預覽，再列印）：

- 頁首：標題「2026 行銷年度行事曆」+ 目前篩選條件摘要（類別 / 產業 / 搜尋詞）+ 產出日期。
- 主體：12 個月的緊湊表格，每月一個區塊，欄位：`日期 | 名稱 | 類別 | 優先度 | 提前準備 | 建議渠道`。
- 內容**跟隨目前篩選結果**；無事件的月份仍顯示月份標題與「無事件」。
- 頂部一顆「🖨 列印 / 另存 PDF」按鈕 → 呼叫 `window.print()`。

**列印樣式**（`@media print`）：

| 規則 | 說明 |
|------|------|
| 隱藏 | header 控制項、月份導航、篩選器、倒數橫幅、視圖 tabs、按鈕、footer |
| 版面 | A4 直式、白底黑字（強制 light 配色，不受主題影響）、`#ccc` 表格邊框（既定例外色） |
| 分頁 | 月份區塊 `break-inside: avoid`；每季結束 `break-after: page`（一季一頁，全年 4 頁） |
| 類別 | 類別以文字標示（如「電商」），不依賴色彩辨識 |

**實作備註**：新增 `renderPrint()`；在非列印 tab 直接按瀏覽器 `Cmd+P` 時，`@media print` 亦套用至當前視圖（degrade 可接受，不特別處理）。

### F4 — .ics 匯出（Google Calendar / Apple Calendar 匯入）

**入口**：header 新增「📅 匯出 .ics」按鈕（桌機與手機皆顯示）。

**匯出範圍**：`filterEvents()` 的當前結果（類別 × 產業 × 搜尋交集），讓成員能匯出「只屬於某產業客戶」的行事曆。

**檔名**：`2026行銷行事曆_{產業標籤}.ics`（全產業時為 `2026行銷行事曆_全部.ics`）。

**VCALENDAR 規格**：

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//marketing-calendar//2026//ZH-TW
CALSCALE:GREGORIAN
X-WR-CALNAME:2026 行銷行事曆（{產業標籤}）
X-WR-TIMEZONE:Asia/Taipei
```

**每個事件產生 1 個 VEVENT（全日事件）**：

| 欄位 | 規則 |
|------|------|
| `UID` | `{event.id}@marketing-calendar-2026` |
| `DTSTART;VALUE=DATE` | `2026MMDD`；`DTEND` 為次日（RFC 5545 全日事件規範） |
| `SUMMARY` | `{類別emoji} {name}`（emoji 沿用篩選按鈕：🇹🇼🛒📍🌍📚） |
| `DESCRIPTION` | 類別、優先度、建議提前週數、行銷議題、建議渠道，`\n` 分隔 |

**Lead Time 轉為提前準備事件**：`priority >= 2` 且 `leadWeeks > 0` 的事件，額外產生一個全日 VEVENT：
- 日期：`事件日期 − leadWeeks × 7 天`
- `UID`：`{event.id}-prep@marketing-calendar-2026`
- `SUMMARY`：`🔔【開始準備】{name}（{leadWeeks} 週後）`

> 採「獨立準備事件」而非 `VALARM`，因 Google Calendar 匯入 .ics 時不保留 VALARM 提醒。

**格式要求**：
- 純前端產生（字串組裝 + `Blob` + `URL.createObjectURL` 下載），不引入函式庫。
- 行結尾 CRLF（`\r\n`）；`SUMMARY` / `DESCRIPTION` 內的 `,` `;` `\n` 依 RFC 5545 跳脫；單行超過 75 octets 摺行（縮排一空格）。
- `DTSTAMP` 為匯出當下時間（UTC）。

**驗收標準**：產出檔案匯入 Google Calendar 與 Apple 行事曆皆無錯誤、無亂碼，事件與準備提醒日期正確。

### F5 — 週報 bot（團隊頻道自動摘要）

**目標**：每週一早上，把「近期檔期 + 該開始準備的事項 + 本月 CPM 警示」主動推到團隊頻道，成員不用記得打開網站。

**架構**：

```
GitHub Actions（cron 排程，每週一 09:00 Asia/Taipei = 01:00 UTC）
  └── 執行 scripts/weekly_digest.py
        ├── 讀取 Google Sheets pub CSV（沿用 script.js CONFIG 同一組 PUBLISHED_ID / GID）
        ├── 讀取失敗 → 改用 script.js 內的 Fallback 常數（解析 JS 檔取出，或維護鏡像資料，實作時擇一）
        ├── 組出摘要訊息
        └── POST 到 webhook（URL 存於 GitHub Secrets：DIGEST_WEBHOOK_URL）
```

**訊息內容**（繁體中文）：

1. **📅 未來 4 週檔期**：依日期排序，`priority >= 2` 全列，`priority 1` 僅列 `tw` / `ec` 類別。
2. **🔔 本週該開始準備**：`準備開始日`（事件日期 − leadWeeks×7）落在本週（週一至週日）的事件清單。
3. **⚡ 本月 CPM 警示**：當月 `level` 非 `normal` 時顯示 `msg`，否則省略此段。
4. 尾行附上網站連結。

**技術要求**：
- Python 3 標準函式庫（`urllib`、`csv`、`datetime`），**零第三方依賴**。
- Webhook 格式預設 Slack Incoming Webhook（`{"text": "..."}`）；若團隊用 LINE，改接 LINE Messaging API push（LINE Notify 已停用，不可採用），以環境變數 `DIGEST_PLATFORM=slack|line` 切換。
- workflow 支援 `workflow_dispatch` 手動觸發（測試用）。
- 執行失敗依 GitHub Actions 預設通知（email），不另建監控。
- 無事件的週仍發送（至少含第 3 段或「本週無新檔期」），確保 bot 存活可被察覺。

---

## 3. 資料結構

**本版本不新增任何資料表、不修改事件欄位。** 所有新功能使用既有欄位：

| 功能 | 使用的既有欄位 |
|------|---------------|
| F1 季度概覽 | `month`, `priority`, `topics`, `cat` + `CPM_ALERTS.level` |
| F2 倒數整合 | `priority`, `leadWeeks` + `CPM_ALERTS.level/msg` |
| F3 列印 | 全事件欄位 |
| F4 .ics | `id`, `month`, `day`, `name`, `cat`, `priority`, `leadWeeks`, `topics`, `channel` |
| F5 週報 | 同 F4 + `CPM_ALERTS` |

前置資料檢查（開發 F2/F4/F5 前完成）：確認 `FALLBACK_EVENTS` 與 Google Sheets 中所有 `priority >= 2` 事件的 `leadWeeks` 都有合理值（缺值視為 0，即不產生準備提醒）。

---

## 4. 檔案結構（v3 之後）

```
行銷年度行事曆/
├── index.html                        # F1–F4 的 HTML 結構（既有檔案內擴充）
├── style.css                         # 季度面板 / 列印樣式（既有檔案內擴充）
├── script.js                         # 渲染 / .ics 產生邏輯（既有檔案內擴充）
├── server.py                         # 本地開發伺服器（不變）
├── scripts/
│   └── weekly_digest.py              # F5 週報 bot（新增）
├── .github/workflows/
│   └── weekly-digest.yml             # F5 排程（新增，cron: '0 1 * * 1'）
├── SDD.md                            # v2.0 既有功能規格
├── SDD-v3.md                         # 本文件
└── ideas/                            # 決策脈絡文件
```

---

## 5. 開發里程碑

依 `CLAUDE.md` 規範，**每個里程碑 = 一個 GitHub Issue + 一條 `task/*` 分支 + 一個 PR**，依序進行：

### M1 — Q1–Q4 季度概覽面板（F1）
- [ ] `renderQuarterOverview()`：季度統計計算（火焰 / 重點事件 / 議題標籤）
- [ ] 面板 UI + RWD（4 欄 / 2×2）+ 點擊捲動
- [ ] 跟隨篩選重繪 + 空狀態

### M2 — 倒數橫幅整合（F2）
- [ ] 倒數項目加 CPM 徽章與準備提醒（含已進入準備期樣式）
- [ ] 當月 `high`/`extreme` 整幅警示列
- [ ] 前置：補齊 `priority >= 2` 事件的 `leadWeeks` 值

### M3 — 列印視圖（F3）
- [ ] 第 4 個 tab + `renderPrint()` + `cal_view` 擴充
- [ ] `@media print` 樣式（A4、一季一頁、強制亮色）
- [ ] 實際列印 / 另存 PDF 驗證

### M4 — .ics 匯出（F4）
- [ ] .ics 字串產生器（含跳脫、摺行、CRLF）
- [ ] 提前準備事件產生邏輯
- [ ] 匯出按鈕 + 檔名規則
- [ ] Google Calendar 與 Apple 行事曆匯入驗收

### M5 — 週報 bot（F5）
- [ ] `scripts/weekly_digest.py`（讀 CSV → 組訊息 → POST webhook，零依賴）
- [ ] `.github/workflows/weekly-digest.yml`（cron + workflow_dispatch）
- [ ] `DIGEST_WEBHOOK_URL` Secret 設定 + 手動觸發實測收到訊息

### M6 — 文件同步
- [ ] `CLAUDE.md` / `.claude.md`：三檔規則補充 `scripts/` 例外、新增 F1–F5 的開發慣例
- [ ] `SDD.md` 頂部加註 v3 擴充指引（指向本文件）

---

## 6. 品質要求

沿用 `SDD.md` §8 全部要求，另加：

- **F1–F4 不引入任何函式庫或新前端檔案**；`index.html` 直開（file://）仍可運作（.ics 下載除外，需 http 環境）。
- **.ics 相容性**：Google Calendar、Apple 行事曆匯入零錯誤，中文無亂碼（UTF-8）。
- **列印**：A4 直式 4 頁內排完全年（未篩選狀態），黑白印表機可辨識類別。
- **週報 bot**：Google Sheets 讀取失敗時 fallback 資料仍能發出訊息，不得靜默失敗。
- **效能**：季度概覽與倒數擴充皆為 O(事件數) 計算，不得引入額外網路請求。

---

## 7. 驗收與成功指標（內部工具視角）

- 團隊成員能在 3 個動作內完成「篩出客戶產業 → 匯出 .ics → 出現在自己的 Google Calendar」。
- 週報 bot 連續 4 週準時送達團隊頻道。
- 年度提案時能直接列印（或存 PDF）指定產業的全年檔期表。
- 上述達成後**即為 v3 終點**——不因「還可以再加」而擴充範圍，新需求回到 `ideas/` 討論。
