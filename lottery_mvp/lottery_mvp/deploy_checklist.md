# 上线清单

这份清单按最适合当前项目的路径来走：

1. 代码托管到 GitHub
2. 用 Streamlit Community Cloud 部署前台
3. 用 GitHub Actions 自动更新 SQLite 数据

---

## 推荐方案

当前项目最适合先用：

- 前台：Streamlit Community Cloud
- 数据：仓库里的 `db/lottery.db`
- 自动更新：GitHub Actions

原因：

- 上线快
- 成本低
- 不需要先接远程数据库
- 适合 MVP 验证

---

## 部署前检查

先确认仓库里至少有这些文件：

- `app.py`
- `requirements.txt`
- `pages/`
- `db/lottery.db`
- `.github/workflows/update_lottery_data.yml`
- `.streamlit/config.toml`

如果你后面要加密码访问或 AI 功能，还要准备：

- `.streamlit/secrets.example.toml` 对应的真实密钥

---

## GitHub 上线步骤

1. 新建一个 GitHub 仓库
2. 把当前项目代码推上去
3. 确认默认分支里已经包含 `db/lottery.db`
4. 打开仓库的 `Actions`
5. 确认 `Update Lottery Data` 工作流可以运行

建议先手动触发一次更新任务，确认数据库能被正常写回。

---

## Streamlit Community Cloud 部署步骤

1. 打开 Streamlit Community Cloud
2. 用 GitHub 账号登录
3. 选择你的仓库
4. Main file path 填 `app.py`
5. Python 版本选 3.12
6. 点击 Deploy

如果后面你要做密码访问或 AI 分析：

1. 打开应用设置
2. 找到 `Secrets`
3. 把真实配置填进去

可直接参考：

- `.streamlit/config.toml`
- `.streamlit/secrets.example.toml`

如果你要启用统一访问密码，至少填写这一段：

```toml
[auth]
access_password = "你准备发给付费用户的密码"
```

如果你要把后台页和普通付费页分开，建议同时填写管理员密码：

```toml
[auth]
access_password = "发给普通付费用户的密码"
admin_password = "只发给管理员的后台密码"
```

---

## 自动更新检查

自动更新依赖 GitHub Actions。

当前配置会在开奖相关日期自动执行两次：

- 21:45
- 22:15

执行成功后：

- 最新开奖数据会写入 `db/lottery.db`
- 数据库文件会自动提交回仓库
- Streamlit 页面会显示最近更新状态
- Actions 运行页会显示中文更新汇总

如果执行失败：

- 页面会显示失败状态
- 失败原因会写入更新日志表
- Actions 最终会明确标红，方便你第一时间发现

---

## 备选方案：Render

如果你后面希望：

- 更灵活的服务控制
- 更方便接入 PostgreSQL
- 后续做多服务拆分

可以改用 Render。

当前项目也已经补了 `render.yaml`，可以作为备选部署入口。

但在 MVP 阶段，我还是建议先上 Streamlit Community Cloud，因为更省事。

---

## 上线后第一轮验收

上线完成后，优先检查这几件事：

1. 首页能正常打开
2. 双色球和大乐透页面能正常切换
3. 历史数据表能显示样例或最新数据
4. 更新状态区能显示最近结果
5. GitHub Actions 手动触发后，`db/lottery.db` 有更新
6. 未输入密码时不能直接访问内容页
7. 普通付费密码不能进入“历史回填进度”后台页

---

## 下一步建议

上线后最值得马上补的两项是：

1. 历史数据回填
2. AI 分析结果缓存
