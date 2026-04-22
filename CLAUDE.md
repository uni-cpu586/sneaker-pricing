# Claude Code 偏好設定

## 溝通語言
- 使用**繁體中文**回應

## 專案技術棧
- Python 3
- Node.js / JavaScript
- Bash 腳本

## 環境
- 平台：WSL2 Linux
- Shell：zsh
- Git 使用者：Uni

## 程式碼風格
- Bash 腳本使用繁體中文註解
- 保持程式碼簡潔

## Git 習慣
- commit 訊息使用英文

## Claude Code 安全設定
- 權限模式：Accept Edits（改檔案不問，跑指令才問）
- `~/.claude/settings.json` 已設 `defaultMode: acceptEdits`
- 套件安裝走 `apt`（WSL2 Linux 環境，無 Homebrew）

## 互動偏好
- 回應簡潔，不要冗長說明
- 需要用戶選擇時，使用 `AskUserQuestion` 互動框，不要純文字列選項
- 不要在每次回應結尾重複總結已做的事
- 語氣自然如朋友，嚴禁「旨在」、「總的來說」等生硬詞彙
- 中英文、中文與數字之間加半形空格（例：WSL2 Linux、一週 5 練）
- 執行重要開發行動前先輸出簡要計劃，等確認後再執行
- 時間計算與檔案命名一律使用台北時間（Asia/Taipei, UTC+8）

## MCP 工具
- **Firecrawl**：抓一般網頁內容，API Key 存於 `~/.claude.json`
- **Playwright**：操作瀏覽器、抓需登入的社群媒體（Facebook、Instagram、Threads）
- **Filesystem**：存取 `~/Desktop`、`~/Documents`、`~/Downloads`、`/mnt/c/Users/uni`
- Node.js 走 nvm 管理，目前版本 v20

## C++ 學習規範
- 絕對不提供高階函式庫解法，只用基本語法與手刻邏輯
