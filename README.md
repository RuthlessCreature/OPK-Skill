# OPK Skill

让任意支持 Skill / Agent 指令的智能体，把 OPK 当作项目状态的外部事实源（source of truth）。

目标闭环：

1. **开始工作前读取 OPK**：项目、里程碑、开放问题、下一步。
2. **执行任务时参考真实状态**：避免重复做、忽略阻塞或使用过期上下文。
3. **工作完成后强制回写 OPK**：更新项目状态、里程碑、问题、next_action 和 notes。
4. **回读验证**：只有 OPK API 返回成功并再次读回一致状态，Agent 才能声称“已同步”。

默认 OPK API：`https://mes.fhkq.best`

## 最快使用

```bash
git clone https://github.com/RuthlessCreature/OPK-Skill.git
cd OPK-Skill
export OPK_API_KEY='你的 OPK Bearer API Key'
python scripts/opk.py dashboard
```

如果当前代码仓库对应一个固定 OPK 项目，在该项目根目录创建 `.opk.json`：

```json
{
  "base_url": "https://mes.fhkq.best",
  "project_id": "你的 OPK project id"
}
```

然后：

```bash
python /path/to/OPK-Skill/scripts/opk.py context --config .opk.json
```

## 给 Agent 加载

把本仓库的 `SKILL.md` 作为 Skill 指令加载，并确保 Agent 能运行：

```bash
python /path/to/OPK-Skill/scripts/opk.py ...
```

环境变量：

- `OPK_API_KEY`：必填。OPK REST API Bearer Key。
- `OPK_BASE_URL`：可选，默认 `https://mes.fhkq.best`。
- `OPK_PROJECT_ID`：可选，固定当前工作对应的 OPK 项目。
- `OPK_PROJECT_NAME`：可选，在没有 project id 时用于搜索项目。

**不要把 `OPK_API_KEY` 写进仓库。**

## 常用命令

```bash
# 总览
python scripts/opk.py dashboard

# 查询项目
python scripts/opk.py projects --q "项目名"

# 读取一个项目完整上下文
python scripts/opk.py context --project-id <id>

# 新建项目
python scripts/opk.py create-project --name "项目名" --priority high --next-action "下一步"

# 更新项目
python scripts/opk.py update-project <id> --status active --next-action "新的下一步" --notes "进展说明"

# 新增里程碑
python scripts/opk.py add-milestone <project-id> --title "联调完成" --status done

# 更新里程碑
python scripts/opk.py update-milestone <milestone-id> --status done --notes "已通过验收"

# 新增问题
python scripts/opk.py add-issue <project-id> --title "接口超时" --severity high --status open --next-action "排查上游"

# 更新问题
python scripts/opk.py update-issue <issue-id> --status resolved --notes "已修复"
```

## Agent 行为约定

详见 [`SKILL.md`](./SKILL.md)。最重要的规则只有两条：

- **做事前先读 OPK。**
- **做完后必须写 OPK 并回读验证。**

如果 API 调用失败，Agent 必须明确报告失败，不能假装已经同步。
