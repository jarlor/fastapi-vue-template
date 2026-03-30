# Git 工作流

本文档定义项目的 Git 分支策略与协作规范。根据团队规模选择合适的模型。

---

## 一、Simple Model（个人 / 小团队）

适用场景：1-3 人开发，无 staging 环境需求。

### 分支结构

```
main ← feature/xxx
main ← fix/xxx
```

`main` 是唯一的长期分支，始终保持可部署状态。

### 工作流程

```bash
# 1. 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/user-auth

# 2. 开发 & 提交（遵循 commit 规范）
git add src/app_name/api/auth.py
git commit -m "feat: add JWT authentication endpoint"

# 3. 推送并创建 PR
git push -u origin feature/user-auth
gh pr create --title "feat: add JWT authentication" --body "..."

# 4. Review 通过后 Merge（squash 或 merge commit 均可）
# 5. 删除远程分支
git push origin --delete feature/user-auth
```

### 要点

- 功能分支生命周期尽量短（1-3 天）
- PR 合并前确保 CI 通过
- 合并后立即删除远程分支

---

## 二、Standard Model（团队 + Staging 环境）

适用场景：多人协作，需要 staging 验证。

### 分支结构

```
main (production) ← develop (staging) ← feature/xxx
                                       ← fix/xxx
main ← hotfix/xxx → merge back to develop
```

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 生产环境，仅通过 PR 合入 | 必须 review + CI 通过 |
| `develop` | 集成分支 / staging | 必须 CI 通过 |
| `feature/*` | 功能开发 | 无 |
| `hotfix/*` | 生产紧急修复 | 无 |

### 功能开发流程

```bash
# 从 develop 创建
git checkout develop
git pull origin develop
git checkout -b feature/model-scoring

# 开发完成后推送
git push -u origin feature/model-scoring

# 创建 PR → develop
gh pr create --base develop --title "feat: add model scoring system"
```

### 发布流程

```bash
# develop 验证通过后，创建 PR: develop → main
gh pr create --base main --head develop --title "release: v1.2.0"

# 合并后打 tag
git checkout main && git pull
git tag v1.2.0
git push origin v1.2.0
```

### Hotfix 流程

```bash
# 从 main 创建 hotfix
git checkout main
git checkout -b hotfix/fix-auth-crash

# 修复后同时合入 main 和 develop
gh pr create --base main --title "fix: auth crash on expired token"
# main 合并后，cherry-pick 或创建第二个 PR → develop
```

---

## 三、Commit 规范

格式：`<type>: <description>`

```
feat: add model approval workflow
fix: correct pagination offset in model list
refactor: extract provider factory from service layer
docs: add SSE streaming guide
test: add integration tests for pipeline API
chore: upgrade FastAPI to 0.115
perf: batch MongoDB writes in metrics collector
ci: add pre-commit hooks to CI pipeline
```

### 规则

- type 必填，使用英文小写
- description 用英文，简洁描述变更目的（不是变更内容）
- 不超过 72 字符
- 可选 body 换行后补充细节

```bash
git commit -m "feat: add webhook notification for model status change

Sends POST to configured webhook URL when a model is approved or rejected.
Supports Feishu, DingTalk, and Slack payload formats."
```

---

## 四、Pull Request 规范

### 标题

简洁、准确，与 commit type 对应：

```
feat: add model scoring API
fix: resolve duplicate entries in parsed collection
```

### 正文模板

```markdown
## Summary
- 简述变更目的和范围

## Changes
- 具体改动列表

## Test Plan
- [ ] 单元测试通过
- [ ] 相关 API 手动验证
- [ ] 无破坏性变更
```

---

## 五、冲突解决

始终用 rebase 保持线性历史：

```bash
# 在功能分支上 rebase 目标分支
git checkout feature/my-feature
git fetch origin
git rebase origin/main   # 或 origin/develop

# 解决冲突后
git add .
git rebase --continue

# force-push 功能分支（仅限功能分支！）
git push --force-with-lease origin feature/my-feature
```

**注意**：`--force-with-lease` 比 `--force` 安全，会检查远程是否有他人的新提交。

---

## 六、禁止事项

| 操作 | 原因 |
|------|------|
| `git push --force` on `main` / `develop` | 破坏他人工作，不可恢复 |
| `git commit --no-verify` | 跳过 pre-commit hooks（lint / format） |
| 提交 `.env` 或密钥文件 | 安全风险，一旦入库无法完全清除 |
| 直接 push 到 `main` | 绕过 review 流程 |
| 超大 PR（500+ 行变更） | 难以 review，拆分为多个小 PR |

---

## 七、常用命令速查

```bash
# 查看分支状态
git log --oneline --graph -20

# 暂存当前工作
git stash
git stash pop

# 修改最近一次 commit message（未 push 时）
git commit --amend -m "fix: corrected message"

# 查看某个文件的变更历史
git log --follow -p -- src/app_name/api/v1/models.py

# 清理已合并的本地分支
git branch --merged main | grep -v main | xargs git branch -d
```
