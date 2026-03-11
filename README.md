# ⚔️ 福爾摩沙 Tier List DataBase Bot 

[![Minecraft Version](https://img.shields.io/badge/Minecraft-1.9+-green.svg)](https://www.minecraft.net/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289DA.svg)](https://discord.gg/hamescZvtP)
[![Status](https://img.shields.io/badge/Status-Official-blue.svg)]()

本專案是由 **ItzSilicon** 開發，目前已由 **福爾摩沙伺服器 (Formosa)** 正式徵用。本機器人專為 **福爾摩沙 Tier List (FTL)** 社群打造，旨在提供玩家便捷的 Tier 查詢、排名追蹤、AI 互動輔助及自動化考試管理功能。

## 🚀 核心功能

* **實時 Tier 查詢 (`/tier`)**：串接官方資料庫，一鍵查看玩家在各項 PVP 模式（Sword, UHC, Axe, NPot 等）的等級與詳細數據。
* **全域排名系統 (`/rank`)**：查看社群內「核心積分」與「全域積分」的即時排行榜，激發競爭力。
* **AI 智能互動輔助**：
    * **Gemini 核心驅動**：整合 Google Gemini 大語言模型，支援透過提及 (Mention) 或指令進行自然語言對話。
    * **加密隱私保護**：支援使用者自定義 API Key，並採用 Fernet 加密技術確保金鑰安全。
    * **在地知識庫 (RAG)**：初步整合 ChromaDB，未來將支援更精準的社群規則與百科檢索。
* **帳號綁定與驗證**：
    * **Hypixel 身份驗證**：透過 Hypixel API 確保玩家身分真實性。
    * **自動化連結**：於伺服器參與考試時，系統將自動綁定 Discord 帳號，簡化行政流程。
* **考官專用自動化工具**：
    * **快速登記系統**：考官可直接透過指令變更 Tier 與成績，系統將自動同步並透過私訊 (DM) 發送美觀的 Embed 結果報告給受試者。
* **豐富的視覺化呈現**：提供多達 13 種不同的 Minecraft 皮膚渲染模式（如 `isometric`, `dungeons` 等），讓查詢結果更具個性化。

## 🛠️ 技術架構

* **語言與框架**：[discord.py](https://github.com/Rapptz/discord.py)
* **資料庫儲存**：SQLite3 (用於 Tier 數據) 與 SQLAlchemy + PostgreSQL/SQLite (用於 AI 聊天數據)
* **AI 模型**：Google Gemini API
* **向量檢索**：ChromaDB
* **安全性**：Fernet 對稱加密

## 📈 項目現況

本專案目前由福爾摩沙伺服器營運團隊維護與使用。為確保系統穩定性與數據安全性，**目前不提供自架教學與環境設定文檔**。

### 意見回饋與檢視
如果您對機器人有任何功能上的建議，或在使用過程中發現 Bug，歡迎透過以下方式回饋：
1.  前往 [福爾摩沙 Discord 伺服器](https://discord.gg/hamescZvtP) 聯繫開發者 **ItzSilicon**。
2.  在 GitHub 提交 **Issue** 進行技術性檢視。

---
*Copyright © 2025-2026 ItzSilicon. All rights reserved.*