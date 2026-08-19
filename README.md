# OPK Skill

让任意 Agent 直接把 OPK 当成项目状态的外部事实源（source of truth）。

默认 API：

```text
https://mes.fhkq.best
```

**OPK `/api/v1/*` 不需要 API Key。**

## 核心闭环

1. **首次接入先查重**：查询 OPK 是否已有同名/相似项目。
2. **有候选就停止写入并问用户**：用户选择“新提交”或“覆盖已有项目”。
3. **无候选则自动建项目**：先拿新的 `project_id`，再创建项目并写入映射。
4. **开始工作前读取 OPK**：项目、里程碑、问题、下一步。
5. **工作完成后自动回写 OPK**。
6. **回读验证**：只有 API 写入成功且读回一致，Agent 才能说“OPK 已同步”。

## 最快使用

```bash
git clone https://github.com/RuthlessCreature/OPK-Skill.git
cd OPK-Skill
python scripts/opk.py dashboard
```

不需要配置 `OPK_API_KEY`。

可选环境变量：

```text
OPK_BASE_URL=https://mes.fhkq.best
OPK_PROJECT_ID=<固定项目ID>
OPK_PROJECT_NAME=<项目名/搜索提示>
```

## 第一次把项目提交到 OPK

推荐直接使用：

```bash
python scripts/opk.py init-project \
  --name "项目名称" \
  --priority high \
  --next-action "下一步动作"
```

这个命令会先调用相似项目查询。

### 情况 A：没有同名/相似项目

自动执行：

```text
GET /api/v1/projects/similar?q=...
→ POST /api/v1/project-ids
→ POST /api/v1/projects
→ GET /api/v1/projects/:id 验证
→ 写入 .opk.json
```

### 情况 B：查到同名/相似项目

不会自动新建，也不会自动覆盖。CLI 会返回：

```text
status = needs_user_decision
```

Agent 必须把候选项目告诉用户，由用户选择：

- **新提交**：创建一个新的 project-id
- **覆盖**：更新用户指定的已有 project-id

用户选择新提交后：

```bash
python scripts/opk.py init-project --name "项目名称" --new
```

用户选择覆盖后：

```bash
python scripts/opk.py init-project --name "项目名称" --overwrite <project-id>
```

“覆盖”只更新已有项目本体，**保留其已有里程碑和问题历史**。

## `.opk.json`

项目成功初始化后，CLI 默认在当前目录写：

```json
{
  "base_url": "https://mes.fhkq.best",
  "project_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "project_name": "项目名称"
}
```

之后 Agent 可以直接：

```bash
python /path/to/OPK-Skill/scripts/opk.py context
```

## 常用命令

```bash
# 总览
python scripts/opk.py dashboard

# 生成新的 project-id
python scripts/opk.py new-project-id

# 查相同/相似项目
python scripts/opk.py similar "项目名称"

# 项目完整上下文
python scripts/opk.py context --project-id <id>

# 安全首次提交
python scripts/opk.py init-project --name "项目名称" --next-action "下一步"

# 更新项目
python scripts/opk.py update-project <id> --status active --next-action "新的下一步" --notes "进展说明"

# 新增/更新里程碑
python scripts/opk.py add-milestone <project-id> --title "联调完成" --status done
python scripts/opk.py update-milestone <milestone-id> --status done --notes "已验证"

# 新增/更新问题
python scripts/opk.py add-issue <project-id> --title "接口超时" --severity high --status open --next-action "排查上游"
python scripts/opk.py update-issue <issue-id> --status resolved --notes "已修复"
```

## API

Skill 直接依赖 OPK REST API，详细接口见：

- [`API.md`](./API.md)
- `https://mes.fhkq.best/openapi.json`

关键接口：

| Method | Path | 作用 |
|---|---|---|
| GET | `/api/v1/dashboard` | 项目总览 |
| POST | `/api/v1/project-ids` | 生成新的 project-id |
| GET | `/api/v1/projects/similar?q=NAME` | 查同名/相似项目 |
| GET / POST | `/api/v1/projects` | 查询 / 新建项目 |
| GET / PATCH / DELETE | `/api/v1/projects/:id` | 项目详情 / 更新 / 删除 |
| GET / POST | `/api/v1/projects/:id/milestones` | 里程碑 |
| PATCH / DELETE | `/api/v1/milestones/:id` | 更新 / 删除里程碑 |
| GET / POST | `/api/v1/projects/:id/issues` | 项目问题 |
| PATCH / DELETE | `/api/v1/issues/:id` | 更新 / 删除问题 |
| GET | `/api/v1/export` | 全量导出 |

## Agent 行为约定

详见 [`SKILL.md`](./SKILL.md)。最关键的规则：

- **首次写入先查重。**
- **查到相似项目必须让用户决定新建还是覆盖。**
- **做事前读 OPK。**
- **做完后写 OPK 并回读验证。**
