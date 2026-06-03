# 農村活動推薦系統 — 部署說明

此專案分成前端 (frontend/) 與後端 (backend/)。前端為靜態 HTML/CSS/JS，可部署至 GitHub Pages；後端為 Flask 應用，可部署至 Render 或其他 PaaS。

重要：目前 Google Maps 功能預設為關閉（USE_REAL_MAPS=false）。若要啟用，請在後端環境變數中設定 GOOGLE_MAPS_API_KEY 並把 USE_REAL_MAPS 設為 true，但請勿把金鑰放到前端。

本檔包含快速部署步驟（本機開發、GitHub Pages、Render 範例）。

本機開發測試
1. 建立虛擬環境並安裝依賴：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

2. 啟動後端（開發）
```powershell
cd backend
python app.py
# 伺服器會在 http://127.0.0.1:5004
```

3. 在瀏覽器打開前端 (同一台機器)：
 - 直接瀏覽 http://127.0.0.1:5004/ (Flask 會提供前端靜態檔案)
 - 或本機打開 frontend/index.html（注意：file:// 下同源限制會阻擋 API 呼叫）

測試 API

GitHub Pages（前端）
1. 若要使用 GitHub Pages，兩種簡單方式：
  - 方法 A（推薦）：把 frontend/ 內容複製到 repo 的 `docs/` 資料夾並在 GitHub Pages 設定中選擇 `main branch /docs folder`。
  - 方法 B：使用 gh-pages branch，將 frontend/ 建立成靜態站並推到 gh-pages 分支。可以用 `gh-pages` 工具或手動。
2. 注意 API_BASE：前端預設會在本機 (localhost) 使用 `http://127.0.0.1:5004`。上線時需在 index.html 中或在部署流程替換 `window.__API_BASE__`（例如在 GitHub Pages 的 index.html 直接加入 `<script>window.__API_BASE__='https://your-backend.example.com'</script>`）。

Render（後端）快速上線
1. 在 Render 建立一個新的 Web Service，選擇連接到 GitHub repository。
2. Build command: `pip install -r backend/requirements.txt`
3. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. 設定環境變數：
   - `CORS_ORIGINS` 可設為 `*` 或指定前端網域
   - `USE_REAL_MAPS` 預設 `false`
   - `GOOGLE_MAPS_API_KEY`（如果需要）
5. 若使用 SQLite，注意 Render 的 ephemeral filesystem（會在重啟消失）。建議改為外部 DB（Postgres）或把資料持久化到外部儲存；目前 repo 的 `db.init_db()` 會在啟動時覆寫本地 `app.db`，不適合生產，部署前請移除或改為條件初始化。

測試前後端連線
1. 啟動後端並確保 `GET /api/health` 回 200。
2. 從部署後的前端（GitHub Pages）訪問時，前端必須將 `window.__API_BASE__` 設為後端 URL，或其他方法讓 `main.js` 知道 API 位址。
3. 若跨域請求被阻擋：在後端設置 `CORS_ORIGINS` 為正確前端網域或 `*`，檢查瀏覽器 console 的 CORS 錯誤。

常見排查項目

若要我幫忙：我可以替你把 `window.__API_BASE__` 直接內嵌到 `frontend/index.html`（上線前替換），或用 GitHub Actions 自動化部署到 gh-pages。請告訴我你要哪種流程。
# 農村活動推薦系統 MVP

第一版骨架：Flask + SQLite + HTML/CSS/JavaScript。

## 啟動方式

1. 進入後端資料夾：
   `cd backend`
2. 安裝套件：
   `pip install -r requirements.txt`
3. 啟動：
   `python app.py`
4. 開啟瀏覽器：
   `http://127.0.0.1:5004`

## 目前包含

