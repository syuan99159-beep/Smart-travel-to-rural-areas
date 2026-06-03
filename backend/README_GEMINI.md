Gemini Integration (後端樣板)
================================

這個檔案說明如何在本專案啟用一個最小可運作的 Gemini（Google Generative API）後端樣板。

環境變數
- `GEMINI_API_KEY`：必須，使用 Google API Key（授權呼叫 Generative API）。
- `GEMINI_MODEL`：選填，預設 `models/text-bison-001`。

新增檔案
- `backend/services/gemini_service.py`：呼叫 Google Generative API 的簡單 wrapper
- `backend/services/assistant_context.py`：將最近的 `query_logs` 與使用者問題組成 prompt
- `backend/routes/assistant.py`：提供 POST `/api/assistant/message` 的 API

簡單測試
1. 在虛擬環境中啟動 Flask（假設已安裝 requirements）：

```powershell
set GEMINI_API_KEY=YOUR_API_KEY_HERE
python -m backend.app
```

2. 用 curl 呼叫 API（或使用 Postman）：

```bash
curl -X POST http://127.0.0.1:5003/api/assistant/message \
  -H "Content-Type: application/json" \
  -d '{"message": "南投哪裡適合親子同遊？"}'
```

回傳格式
- 成功：`{"success": true, "text": "...", "raw": {...}}`
- 失敗：`{"success": false, "error": "..."}`

注意事項
- 這是最小樣板，實務上應加入：
  - 請求速率限制、認證、日誌與審計。
  - Prompt 模板管理與截斷/摘要策略（避免長 prompt 超出限制）。
  - 使用 OAuth/Service Account 的授權流程以提高安全性（若使用 GCP 底層 SDK）。
