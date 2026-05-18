# 多彩种低成本云端网页 MVP

这是一个基于 Streamlit 的彩票数据分析网站原型，包含：

- 双色球
- 大乐透
- 福彩3D
- 排列3
- 排列5
- 七乐彩
- 快乐8

功能范围：

- 访问码登录与 9.9 元手工收费流程
- 每日 AI 次数限制
- 历史开奖查询
- 频率统计
- 遗漏分析
- 模拟选号
- AI 辅助分析
- CSV 导出
- 管理员后台
- SQLite 低成本部署
- Docker / Render 配置

## 最低成本上线方案

如果你想以最低价格先把收费查询站跑起来，建议直接用这一套：

- 网页：Streamlit Community Cloud
- 数据：SQLite
- 自动更新：GitHub Actions
- 收费：微信/支付宝收款码 + 管理员后台手工发访问码
- AI：限制次数，只做辅助分析与选号解释

这套的重点不是“承诺中奖”，而是做一个可收费打开的统计分析站。

如果你准备上正式版，当前项目已经支持双模式：

- 本地 / 低成本版：SQLite
- Render 正式版：PostgreSQL

## 本地运行

```bash
pip install -r requirements.txt
python updater.py --seed-demo
streamlit run app.py
```

默认演示访问码：

```text
FREE-DEMO
```

默认管理员密码：

```text
admin123
```

建议通过环境变量覆盖：

```bash
export ADMIN_PASSWORD='your-password'
export DATA_DIR='./data'
```

如果要切到 PostgreSQL：

```bash
export DATABASE_URL='postgresql://user:password@host:5432/dbname'
```

项目会优先使用 `DATABASE_URL`，未设置时才回退到 SQLite。

## 生产环境建议

上线前至少做这 4 件事：

1. 把默认管理员密码改掉
2. 删除或停用 `FREE-DEMO` 演示访问码
3. 在 Streamlit Cloud 或 Render 中配置环境变量
4. 启用 GitHub Actions，每天自动跑更新

## 访问码收费流程

推荐最轻量的流程：

1. 用户看到收款码并支付 9.9 元
2. 用户填写付款备注或订单号
3. 管理员在后台查看订单
4. 管理员生成访问码并发给用户
5. 用户输入访问码后才能看完整查询和 AI 分析

## AI 成本控制

建议这样控制：

- 免费码：每天 1 次 AI
- 付费码：每天 5 次 AI
- AI 只做趋势摘要、号码点评、选号解释
- 选号本体优先用本地规则和统计逻辑生成

## 自动更新入口

初始化演示数据：

```bash
python updater.py --seed-demo
```

执行一次更新：

```bash
python updater.py --run-once
```

正式接入时，将 `data_service.py` 中的演示生成逻辑替换为真实开奖源采集逻辑即可。

当前版本已经带有“先尝试官方源”的更新逻辑：

- 福彩：`cwl.gov.cn`
- 体彩：`lottery.gov.cn`

如果运行环境无法抓取官方源：

- `ALLOW_DEMO_FALLBACK=1`：自动回退到演示数据，便于继续调试页面
- `ALLOW_DEMO_FALLBACK=0`：更新失败时直接报错，适合正式环境排查

说明：

- 官方网页存在反爬或结构变动风险，首次上线前建议先在你自己的服务器或 GitHub Actions 上跑一次 `python updater.py --run-once`
- 如果某个彩种抓取不稳定，可以通过环境变量覆盖对应来源地址，例如 `SOURCE_URL_SSQ`、`SOURCE_URL_DLT`

## GitHub Actions 自动更新

仓库里已经包含：

`./.github/workflows/daily-update.yml`

默认会在每天中国时间 `22:30` 和 `23:10` 各执行一次更新。  
这适合先用最低成本跑通“自动更新 + 在线查询”的闭环。

## Docker 启动

```bash
docker build -t lottery-mvp .
docker run -p 8501:8501 \
  -e ADMIN_PASSWORD='your-password' \
  -v $(pwd)/data:/app/data \
  lottery-mvp
```

## Render 部署

仓库里已经包含：

`render.yaml`

可直接作为 Render Blueprint 起步，包含：

- 一个 PostgreSQL 数据库
- 一个 Web 服务
- 一个每日更新 Cron Job

这版已经适合从 SQLite 平滑迁到 Render + PostgreSQL：

1. 在 Render 创建 Blueprint
2. 系统自动创建 Postgres、Web、Cron
3. Web 和 Cron 都读取同一个 `DATABASE_URL`
4. 数据更新不再依赖 SQLite 文件或持久化磁盘

如果你要继续压缩成本，优先使用 Streamlit Community Cloud + GitHub Actions。  
如果你要更稳定的自动任务和更适合多用户访问的数据库，直接切 Render + PostgreSQL。
