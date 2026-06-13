# 部署到 Oh My Pi (omp)

## 前提

- 已安装 omp
- 工作目录已知（通常是你的项目根目录）

## 步骤

### 1. 启用记忆后端

在 `~/.omp/agent/config.yml` 中添加：

```yaml
memory:
  backend: local
```

### 2. 找到记忆路径

`memory://root` 在 omp 中解析为 `~/.omp/agent/memories/<项目标识>/`。

项目标识是工作目录路径的编码形式。例如 `C:/tmp` → `--C--tmp--`。

### 3. 部署记忆文件

```bash
cp MEMORY.md ~/.omp/agent/memories/<项目标识>/MEMORY.md
cp memory_summary.md ~/.omp/agent/memories/<项目标识>/memory_summary.md
```

### 4. 部署 skill（可选，给其他 agent 用）

```bash
mkdir -p ~/.omp/skills/mneme
cp skills/mneme/SKILL.md ~/.omp/skills/mneme/SKILL.md
```

### 5. 重启 omp

下一次会话启动时，记忆管道会处理这些文件。`memory_summary.md` 会被注入到系统 prompt 中。

## ⚠️ 重要：记忆管道会覆盖手动编辑

omp 的记忆管道（local backend）在**每次启动时**从会话记录中重新生成 MEMORY.md。这是设计行为——管道拥有 MEMORY.md 的所有权。后果：

- 手动添加的「内在成长」部分**会被覆盖**
- 在 `raw_memories.md` 中记录的内容会被保留，不在其中的会被丢弃

**对策：**
1. 将本项目的 MEMORY.md 视为「模板」——每次管道覆盖后，手动将「内在成长」部分追加回去
2. 或将「内在成长」内容写入 `skills/mneme/SKILL.md`，让 agent 从 skill 中读取——skill 不会被管道覆盖
3. 在 omp 的 GitHub 仓库备份完整的 MEMORY.md
