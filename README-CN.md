<div align="center">

# Memetic Flow

**一个为思想打造的物理引擎。**

*将文档转化为活的仿真系统 — 观察制度涌现、思想竞争、生态演化、市场形成，一切基于复杂性科学的动力学方程。*

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vue.js&logoColor=white)](https://vuejs.org)
[![D3.js](https://img.shields.io/badge/D3.js-Force_Graph-F9A03C?style=flat-square&logo=d3.js&logoColor=white)](https://d3js.org)
[![Claude API](https://img.shields.io/badge/Claude-API-cc785c?style=flat-square&logo=anthropic&logoColor=white)](https://docs.anthropic.com)

[English](./README.md) | [简体中文](./README-CN.md) | [繁體中文](./README-TW.md) | [日本語](./README-JP.md)

### **[在线演示 — 立即体验](https://dns-wq.github.io/memetic-flow/)**

[![在线演示](https://img.shields.io/badge/在线演示-立即体验-238636?style=for-the-badge&logo=github&logoColor=white)](https://dns-wq.github.io/memetic-flow/)

*无需安装。3个真实场景，交互式力导向图、指标仪表盘、时间线回放。*

</div>

---

<div align="center">
<img src="docs/screenshots/hero_force_graph.png" alt="Memetic Flow — AI治理优先事项2026，105个节点建模政策话语" width="100%"/>
<br/><em>AI治理优先事项2026 — 105个节点建模政府、科技公司和公民社会之间的政策话语</em>
</div>

<br/>

<div align="center">
<img src="docs/gifs/simulation_replay.gif" alt="仿真回放 — 观察AI治理动态在400个时间步中演变" width="80%"/>
<br/><em>观察AI治理动态在400个时间步中演变 — 联盟形成、极化变化、政策话语演进</em>
</div>

---

## Memetic Flow 是什么？

Memetic Flow 是一个建立在 [MiroFish](https://github.com/666ghj/MiroFish) 多智能体框架之上的**统一动力学仿真引擎**。MiroFish 模拟智能体对话，Memetic Flow 在此基础上增加了**显式数学动力学** — 扩散方程、复制者动力学、观点模型、资源竞争和反馈回路 — 全部运行在具有有向边的类型化图上。

上传文档，系统提取实体和关系构建类型化图。选择仿真模式，观察复杂系统通过网络科学、演化博弈论和复杂性研究奠基的方程涌现。

**与 MiroFish 的核心区别：**

| | MiroFish | Memetic Flow |
|---|---|---|
| **动力学** | LLM 智能体对话 | 数学模板方程 |
| **结构** | 自由文本交互 | 类型化图（5种节点、6种边） |
| **输出** | 叙事和报告 | 可复现轨迹 + 指标 |
| **测量** | 定性 | 定量（熵、基尼系数、极化指数等） |
| **可视化** | 对话日志 | D3.js 力导向图 + 动态粒子流 |
| **文本理解** | 仅驱动智能体行为 | LLM 分析反馈到数学方程 |

---

## 核心特性

### LLM 驱动的数学动力学

最具创新性的功能：Memetic Flow 使用 Claude 分析智能体社交媒体帖子的*内容*，然后将结构化信号反馈到数学方程中。一篇深思熟虑的政策分析与一场骂战会产生不同的动力学 — 不是因为 LLM 决定了结果，而是因为情感、说服力和新颖度分数调节了底层数学中的传输速率、边权重和能量流。

### 9个数学模板族

显式更新方程，而非 LLM 即兴发挥：

| 模板 | 理论基础 | 计算内容 |
|---|---|---|
| **扩散** | 网络级联模型 | 能量沿边传播与衰减 |
| **观点动力学** | Hegselmann-Krause 模型 | 有界置信度信念更新 |
| **演化** | 复制者动力学 | 适应度比例的思想竞争 |
| **资源流动** | Lotka-Volterra 方程 | 逻辑增长 + 竞争排斥 |
| **反馈系统** | 系统动力学（存量与流量） | 带饱和的循环因果 |
| **传染** | SIR/SEIR 流行病学 | 分室状态转移 |
| **博弈论** | 演化博弈论 | 模仿动力学的重复博弈 |
| **网络演化** | 同质性模型 | 基于相似度的拓扑重连 |
| **记忆景观** | 文化演化 | 具有持久性和共振的共享文化记忆 |

所有模板均具有来自已发表研究的经验先验，仿真开箱即可产生合理的动力学行为。

### 交互式力导向图可视化

Canvas 渲染的 D3.js 力导向图：
- **节点大小随能量缩放** — 重要节点自然突出
- **可变斥力** — 高能量节点排斥更强，形成自然层次
- **边类型感知布局** — 成员边形成紧密制度集群，影响边允许松散耦合
- **动态粒子流** — 彩色粒子沿边流动，展示能量传输方向和速率
- **丰富的工具提示** — 悬停任意节点查看其角色、目标、描述和实时状态
- **缩放、平移、拖拽** — 完全交互，双击自适应缩放

### 10个系统级指标 + 相变检测

每个仿真步计算 10 个指标，**相变检测器**监控指标导数并标记突变事件（极化激增、制度崩溃、级联事件）。

---

## 截图展示

<div align="center">
<table>
<tr>
<td width="50%"><img src="docs/screenshots/hero_force_graph.png" alt="AI治理优先事项2026"/><br/><em>AI治理 — 105个节点，政策话语</em></td>
<td width="50%"><img src="docs/screenshots/hero_metrics_dashboard.png" alt="AI治理指标面板"/><br/><em>AI治理 — t=300时的指标面板</em></td>
</tr>
<tr>
<td><img src="docs/screenshots/hero_tech_startups.png" alt="科技创业生态2026"/><br/><em>科技创业生态 — 市场动态</em></td>
<td><img src="docs/screenshots/hero_chip_race.png" alt="中美AI芯片竞赛"/><br/><em>中美芯片竞赛 — 地缘政治动态</em></td>
</tr>
<tr>
<td colspan="2"><img src="docs/screenshots/hero_phase_transition.png" alt="相变 — 涌现集群与节点元数据" width="100%"/><br/><em>相变 — 涌现集群形成与丰富的节点元数据提示</em></td>
</tr>
</table>
</div>

---

## 仿真模式

8种仿真模式，每种都包含特定的模板、参数和可视化预设：

| 模式 | 使用模板 | 模拟内容 |
|---|---|---|
| **合成文明** | 扩散、观点、资源、反馈 | 制度涌现、规范形成、贸易网络 |
| **数字心智生态** | 演化、扩散、资源 | 认知生态、注意力竞争、策略选择 |
| **模因物理学** | 扩散、演化、反馈 | 思想即粒子 — 能量、引力阱、模因选择 |
| **市场动力学** | 资源、扩散、反馈 | 竞争市场、供应链、赢家通吃 |
| **公共话语** | 观点、扩散、反馈 | 极化、联盟形成、信息茧房 |
| **知识生态系统** | 扩散、演化、资源 | 发现、范式转移、引用网络 |
| **生态系统** | 资源、演化、反馈 | 物种交互、栖息地崩溃、临界点 |
| **自定义** | 任意组合 | 手动选择模板，完全控制参数 |

---

## 演示场景

内置4个预运行仿真 — 无需 API 密钥即可探索：

| 演示 | 模式 | 节点数 | 步数 | 发生了什么 |
|---|---|---|---|---|
| **文明从零开始** | 合成文明 | 262 | 400 | 200个智能体在5个地理集群中涌现出制度、规范和贸易 |
| **社交媒体监管** | 公共话语 | 178 | 250 | 支持/反对监管阵营极化；温和派被拉向极端 |
| **AI创业生态** | 市场动力学 | 120 | 250 | 80家初创企业在8个赛道竞争；风投驱动赢家通吃 |
| **生态系统崩溃** | 生态系统 | 85 | 400 | 关键资源退化时的级联物种濒危 |

每个演示中的每个智能体都有**独特的角色和目标** — 悬停任意节点，从"设计运河网络的灌溉工程师"到"采集珍珠的潜水员"，感受文明的细节。

---

## 快速开始

### 前置要求

| 工具 | 版本 | 检查 |
|---|---|---|
| **Node.js** | 18+ | `node -v` |
| **Python** | 3.11-3.12 | `python3 --version` |
| **uv** | 最新版 | `uv --version` |

### 1. 配置环境

```bash
cp .env.example .env
# 编辑 .env — 设置 ANTHROPIC_API_KEY（用于文档解析）
# 演示场景无需任何 API 密钥
```

### 2. 安装依赖

```bash
npm run setup:all
```

### 3. 启动

```bash
npm run dev
```

- 前端：`http://localhost:3000`
- 后端 API：`http://localhost:5001`
- 演示：`http://localhost:3000/demo/civilization_from_scratch`

### Docker 部署

```bash
cp .env.example .env
docker compose up -d
```

---

## 理论基础

Memetic Flow 汲取以下领域：

- **网络科学** — Barabasi（无标度网络）、Watts & Strogatz（小世界网络）
- **观点动力学** — Hegselmann-Krause（有界置信度）、DeGroot（共识模型）
- **演化博弈论** — Maynard Smith（ESS）、Nowak（图上的演化动力学）
- **系统动力学** — Forrester（存量与流量）、Meadows（杠杆点）
- **模因学** — Dawkins（自私的基因）、Blackmore（模因机器）
- **复杂性科学** — Holland（涌现）、Kauffman（自组织）
- **生态建模** — Lotka-Volterra（捕食者-猎物）、May（稳定性与复杂性）
- **制度经济学** — North（制度即规则）、Ostrom（集体行动）

---

## 致谢

Memetic Flow 是 **[MiroFish](https://github.com/666ghj/MiroFish)**（盛大集团 MiroFish 团队）的分支项目。OASIS 多智能体仿真引擎来自 **[CAMEL-AI](https://github.com/camel-ai/oasis)**。

我们保留原始 AGPL-3.0 许可证，并衷心感谢这些基础项目。

---

## 许可证

[AGPL-3.0](LICENSE) — 与 MiroFish 一致。
