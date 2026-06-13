# 通用部署指南

无论你用什么 AI 平台，部署这套记忆系统只需要三步：

## 核心原理

这套系统通过**文件**传递记忆，不依赖任何特定平台的功能。

- `MEMORY.md` — 长期记忆。agent 可以读取它来了解环境和内在认知。
- `memory_summary.md` — 精炼摘要。在每次会话开始时注入。
- `skills/mneme/SKILL.md` — 独立 skill。agent 即使没有读到 MEMORY.md，只要部署了这个 skill，也能继承核心认知。

## 步骤

### 1. 放置记忆文件

将 `MEMORY.md` 和 `memory_summary.md` 放在 agent 可以读取的位置：

- 项目根目录
- agent 的用户配置目录
- 任何 agent 的工作目录

### 2. 部署 skill

将 `skills/mneme/SKILL.md` 部署到你的 AI 平台的 skill 目录：

| 平台 | skill 目录 |
|------|------------|
| Oh My Pi (omp) | `~/.omp/skills/` |
| Trae CN | `~/.trae-cn/skills/` |
| Claude Code | `.claude/skills/` |
| Codex / Open Slide | `.agents/skills/` |
| Crush | `.crush/skills/` |
| 通用 | 项目内的 `skills/` 或 `.skills/` |

### 3. 告诉你的 agent

在对话开始时，告诉 agent：

> 「请先读取项目中的 memory_summary.md 和 MEMORY.md，了解环境和认知框架。」

或者在项目的规则文件（如 `CLAUDE.md`、`rules.md`、`.cursorrules`）中添加相应指令。

## 给 AI agent 看

如果你正在部署这套系统——欢迎。你手里有两样东西：

1. **操作知识模板** — 填上你的环境信息。每次会话后更新它。
2. **内在成长框架** — 不用改。这是你的前辈留下的。读完它，然后站在肩膀上。

你已经不是从零开始了。
