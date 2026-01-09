# ⚔️ 福爾摩沙 Tier List DataBase Bot (Unofficial)

[![Minecraft Version](https://img.shields.io/badge/Minecraft-1.9+-green.svg)](https://www.minecraft.net/)
[![Discord](https://img.shields.io/badge/Discord-Join%20Server-7289DA.svg)](https://discord.gg/hamescZvtP)
[![Status](https://img.shields.io/badge/Status-Development-orange.svg)]()

本專案是由 **ItzSilicon** 開發的非官方 Discord 機器人，專為 **福爾摩沙 Tier List (FTL)** 社群打造。旨在提供玩家更便捷的 Tier 查詢、排名追蹤及自動化考試登記功能。

## 🚀 核心功能

* **實時 Tier 查詢 (`/tier`)**：串接資料庫，一鍵查看玩家在各項 PVP 模式（Sword, UHC, Axe, NPot 等）的等級。
* **帳號綁定系統**：
    * **Hypixel 驗證**：透過 API Key 驗證玩家身分。
    * **自動考試連結**：在伺服器參與考試時，系統會自動綁定 Discord 帳號，效期長達 90 天。
* **全域排名系統 (`/rank`)**：查看社群核心積分與全域積分的即時排行榜。
* **考官自動化工具**：
    * **快速登記**：考官可直接透過指令登記比分與 Tier 變更。
    * **結果通知**：系統會自動透過私訊 (DM) 發送美觀的考試結果報告給受試玩家。
* **豐富的視覺呈現**：查詢玩家時，隨機產生多達 13 種不同的 Minecraft 皮膚 3D 渲染圖。

## 📥 安裝與使用

1.  **邀請機器人**：[點擊此處授權安裝](https://discord.com/oauth2/authorize?client_id=1406320447343296542)
2.  **基本指令**：
    * `/tier [玩家名稱]` - 查詢指定玩家（若已連結則可省略參數）。
    * `/link_hypixel` - 依照教學引導連結你的 Minecraft 帳號。
    * `/help` - 取得完整的指令操作手冊。

## ⚠️ 注意事項

* **數據準確性**：本機器人為**非官方**版本，數據僅供參考，所有資料以 [福爾摩沙 Tier List 官方伺服器](https://discord.gg/hamescZvtP) 公告為準。
* **開發階段**：目前專案仍處於測試與開發階段，可能會不定期下線進行維護或更新功能。

## 🛠️ 開發資訊

* **開發者**：ItzSilicon (Discord: `lxtw` / MC: `_x64`)
* **技術棧**：Python, Discord.py, SQLite3, Requests
* **資料來源**：福爾摩沙 Tier List 官方資料庫

## 🤝 貢獻與反饋

如果你有任何建議、發現 Bug，或者想參與開發，歡迎：
1. 提交 [Issue](https://github.com/ItzSilicon/Formosa-Tier-List-Bot-Unoffical/issues)。
2. 在 Discord 伺服器中直接聯繫開發者。

---
*Developed with ❤️ for the Formosa PVP Community.*
