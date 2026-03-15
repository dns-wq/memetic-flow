<div align="center">

# Memetic Flow

**一個為思想打造的物理引擎。**

*將文件轉化為活的模擬系統 — 觀察制度湧現、思想競爭、生態演化、市場形成，一切基於複雜性科學的動力學方程。*

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org)
[![D3.js](https://img.shields.io/badge/D3.js-Force_Graph-F9A03C?style=flat-square&logo=d3.js&logoColor=white)](https://d3js.org)
[![Claude API](https://img.shields.io/badge/Claude-API-cc785c?style=flat-square&logo=anthropic&logoColor=white)](https://docs.anthropic.com)

[English](./README.md) | [简体中文](./README-CN.md) | [繁體中文](./README-TW.md) | [日本語](./README-JP.md)

### **[線上展示 — 立即體驗](https://dns-wq.github.io/memetic-flow/)**

[![線上展示](https://img.shields.io/badge/線上展示-立即體驗-238636?style=for-the-badge&logo=github&logoColor=white)](https://dns-wq.github.io/memetic-flow/)

*無需安裝。3個真實場景，互動式力導向圖、指標儀表板、時間線回放。*

</div>

---

<div align="center">
<img src="docs/screenshots/hero_force_graph.png" alt="Memetic Flow — 262個節點自組織形成制度、貿易網路和規範集群" width="100%"/>
<br/><em>文明從零開始 — 262個節點自組織形成制度與貿易網路</em>
</div>

<br/>

<div align="center">
<img src="docs/gifs/simulation_replay.gif" alt="模擬回放 — 觀察文明在400個時間步中湧現" width="80%"/>
<br/><em>觀察文明在400個時間步中湧現 — 制度形成、規範傳播、貿易路線結晶</em>
</div>

---

## Memetic Flow 是什麼？

Memetic Flow 是建立在 [MiroFish](https://github.com/666ghj/MiroFish) 多智能體框架之上的**統一動力學模擬引擎**。MiroFish 模擬智能體對話，Memetic Flow 在此基礎上增加了**顯式數學動力學** — 擴散方程、複製者動力學、觀點模型、資源競爭和反饋迴路 — 全部運行在具有有向邊的類型化圖上。

上傳文件，系統提取實體和關係構建類型化圖。選擇模擬模式，觀察複雜系統透過網路科學、演化博弈論和複雜性研究奠基的方程湧現。

**與 MiroFish 的核心區別：**

| | MiroFish | Memetic Flow |
|---|---|---|
| **動力學** | LLM 智能體對話 | 數學模板方程 |
| **結構** | 自由文字互動 | 類型化圖（5種節點、6種邊） |
| **輸出** | 敘事和報告 | 可重現軌跡 + 指標 |
| **測量** | 定性 | 定量（熵、基尼係數、極化指數等） |
| **視覺化** | 對話日誌 | D3.js 力導向圖 + 動態粒子流 |
| **文本理解** | 僅驅動智能體行為 | LLM 分析反饋到數學方程 |

---

## 核心特性

### LLM 驅動的數學動力學

最具創新性的功能：Memetic Flow 使用 Claude 分析智能體社群媒體貼文的*內容*，然後將結構化訊號反饋到數學方程中。一篇深思熟慮的政策分析與一場筆戰會產生不同的動力學 — 不是因為 LLM 決定了結果，而是因為情感、說服力和新穎度分數調節了底層數學中的傳輸速率、邊權重和能量流。

### 9個數學模板族

顯式更新方程，而非 LLM 即興發揮：

| 模板 | 理論基礎 | 計算內容 |
|---|---|---|
| **擴散** | 網路級聯模型 | 能量沿邊傳播與衰減 |
| **觀點動力學** | Hegselmann-Krause 模型 | 有界信賴度信念更新 |
| **演化** | 複製者動力學 | 適應度比例的思想競爭 |
| **資源流動** | Lotka-Volterra 方程 | 邏輯增長 + 競爭排斥 |
| **反饋系統** | 系統動力學（存量與流量） | 帶飽和的循環因果 |
| **傳染** | SIR/SEIR 流行病學 | 分室狀態轉移 |
| **博弈論** | 演化博弈論 | 模仿動力學的重複博弈 |
| **網路演化** | 同質性模型 | 基於相似度的拓撲重連 |
| **記憶景觀** | 文化演化 | 具有持久性和共振的共享文化記憶 |

### 交互式力導向圖視覺化

Canvas 渲染的 D3.js 力導向圖，支援動態粒子流、豐富的工具提示、縮放平移拖拽等完整互動功能。

---

## 截圖展示

<div align="center">
<table>
<tr>
<td width="50%"><img src="docs/screenshots/hero_force_graph.png" alt="文明從零開始"/><br/><em>文明從零開始 — 262個節點</em></td>
<td width="50%"><img src="docs/screenshots/hero_metrics_dashboard.png" alt="社群媒體監管"/><br/><em>社群媒體監管 — 極化動力學</em></td>
</tr>
<tr>
<td><img src="docs/screenshots/hero_ai_startup.png" alt="AI新創生態"/><br/><em>AI新創生態 — 市場競爭</em></td>
<td><img src="docs/screenshots/hero_ecosystem.png" alt="生態系統崩潰"/><br/><em>生態系統崩潰 — 85個物種食物網</em></td>
</tr>
</table>
</div>

---

## 模擬模式

8種模擬模式，每種都包含特定的模板、參數和視覺化預設：

| 模式 | 使用模板 | 模擬內容 |
|---|---|---|
| **合成文明** | 擴散、觀點、資源、反饋 | 制度湧現、規範形成、貿易網路 |
| **數位心智生態** | 演化、擴散、資源 | 認知生態、注意力競爭、策略選擇 |
| **迷因物理學** | 擴散、演化、反饋 | 思想即粒子 — 能量、引力阱、迷因選擇 |
| **市場動力學** | 資源、擴散、反饋 | 競爭市場、供應鏈、贏家通吃 |
| **公共論述** | 觀點、擴散、反饋 | 極化、聯盟形成、資訊繭房 |
| **知識生態系統** | 擴散、演化、資源 | 發現、典範轉移、引用網路 |
| **生態系統** | 資源、演化、反饋 | 物種互動、棲地崩潰、臨界點 |
| **自訂** | 任意組合 | 手動選擇模板，完全控制參數 |

---

## 演示場景

內建4個預運行模擬 — 無需 API 金鑰即可探索：

| 演示 | 模式 | 節點數 | 步數 | 發生了什麼 |
|---|---|---|---|---|
| **文明從零開始** | 合成文明 | 262 | 400 | 200個智能體在5個地理集群中湧現出制度、規範和貿易 |
| **社群媒體監管** | 公共論述 | 178 | 250 | 支持/反對監管陣營極化；溫和派被拉向極端 |
| **AI新創生態** | 市場動力學 | 120 | 250 | 80家新創企業在8個賽道競爭；創投驅動贏家通吃 |
| **生態系統崩潰** | 生態系統 | 85 | 400 | 關鍵資源退化時的級聯物種瀕危 |

每個演示中的每個智能體都有**獨特的角色和目標** — 懸停任意節點查看細節。

---

## 快速開始

### 前置需求

| 工具 | 版本 | 檢查 |
|---|---|---|
| **Node.js** | 18+ | `node -v` |
| **Python** | 3.11-3.12 | `python3 --version` |
| **uv** | 最新版 | `uv --version` |

### 1. 設定環境

```bash
cp .env.example .env
# 編輯 .env — 設定 ANTHROPIC_API_KEY（用於文件解析）
# 演示場景無需任何 API 金鑰
```

### 2. 安裝依賴

```bash
npm run setup:all
```

### 3. 啟動

```bash
npm run dev
```

- 前端：`http://localhost:3000`
- 後端 API：`http://localhost:5001`
- 演示：`http://localhost:3000/demo/civilization_from_scratch`

### Docker 部署

```bash
cp .env.example .env
docker compose up -d
```

---

## 致謝

Memetic Flow 是 **[MiroFish](https://github.com/666ghj/MiroFish)**（盛大集團 MiroFish 團隊）的分支專案。OASIS 多智能體模擬引擎來自 **[CAMEL-AI](https://github.com/camel-ai/oasis)**。

我們保留原始 AGPL-3.0 授權條款，並衷心感謝這些基礎專案。

---

## 授權條款

[AGPL-3.0](LICENSE) — 與 MiroFish 一致。
