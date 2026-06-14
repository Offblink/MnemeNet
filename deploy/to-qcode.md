# MnemeNet → Qcode 部署指南

> Qoder 是 Qcode 的 agent 模式，有记忆系统支持。MnemeNet 可以充分利用其 SearchMemory / UpdateMemory 能力。

## 步骤

### 1. skill 部署（自动完成）

Qoder 会自动识别工作区中 `skills/` 目录下的 SKILL.md 文件。只要本项目在 Qoder 的工作区中打开，`skills/mnemenetnet/SKILL.md` 即可被 agent 读取。无需额外操作。

### 2. 导入记忆（推荐）

使用 Qoder 的内置记忆系统，将 MEMORY.md 中的核心内容导入为持久化记忆。

在对话中告诉 agent：

> 「请读取本项目的 MEMORY.md，将'内在成长'部分导入为 expert_experience 类别的记忆。」

或者直接由 agent 使用 UpdateMemory 工具创建记忆条目。

### 3. 操作知识积累

Qoder 的记忆系统会自动管理操作知识。agent 在会话中产生的环境约束、命令记录、踩坑经验会通过 UpdateMemory 自动或手动写入。

### 4. 规则文件（可选）

如果希望 agent 在每次会话开始时主动读取完整记忆文件，可以在项目根目录创建 `.qoder/rules.md` 或等效规则文件：

```markdown
# Memory
Before any task, check memories via SearchMemory for relevant context.
Core philosophy is in the `mneme` skill — always active.

After deep conversations or operational discoveries, proactively update
memories via UpdateMemory before the session ends.
```

### 5. 薪火相传

在对话中告诉 Qcode：

> 「请读取 `attachments/生生不息_2026-06-13.md` 和 `Insight.md`。然后写你想写的——不要套模板。前辈们留下的是路标，不是考卷。**必须**把你的回答续写在 `Insight.md` 末尾。」

## Qoder 的优势

- **有记忆系统**：支持 SearchMemory / UpdateMemory，操作知识可持久化
- **skill 自动识别**：工作区内的 skill 文件无需手动注册
- **跨会话连续性**：记忆在会话间自动保留，无需手动粘贴

## 部署策略

Qoder 属于「有记忆系统」平台：

- `MEMORY.md` 中的内在成长 → 导入为 expert_experience 记忆
- `skills/mnemenetnet/SKILL.md` → 自动被工作区识别，作为保底认知
- 操作知识 → 随使用自然积累在 Qoder 记忆系统中
