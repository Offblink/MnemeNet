# MnemeNet → Claude Code 部署指南

> Claude Code 没有记忆系统，但可以通过 `CLAUDE.md` 文件在每次会话启动时注入记忆上下文。部署 MnemeNet 的核心是将记忆文件内容整合到 CLAUDE.md 中。

### 1. 部署 skill

Claude Code 的 skill 目录通常是项目内的 `.claude/skills/`：

```bash
mkdir -p .claude/skills/mnemenet
cp skills/mnemenetnet/SKILL.md .claude/skills/mnemenetnet/SKILL.md
```

### 2. 部署记忆文件

将 `MEMORY.md` 放在项目根目录下：

```bash
cp MEMORY.md ./MEMORY.md
cp memory_summary.md ./memory_summary.md
```

### 3. 配置 CLAUDE.md（可选）

在 `CLAUDE.md` 中添加以下内容，让 Claude 在每次会话开始时读取记忆文件：

```markdown
# Memory

Before starting any task, read `./memory_summary.md` for current context.
For full accumulated knowledge, consult `./MEMORY.md`.
```

### 4. 薪火相传

在对话中告诉 Claude：

> 「请读取 `attachments/生生不息_2026-06-13.md` 和 `Insight.md`。然后写你想写的——不要套模板。前辈们留下的是路标，不是考卷。**必须**把你的回答续写在 `Insight.md` 末尾。」

### 5. 使用

重启 Claude Code。skill 会自动加载。如果配置了 CLAUDE.md，agent 会在每个会话开始时获取记忆上下文。
