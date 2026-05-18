# 多彩种低成本云端网页 MVP · 第二版

这是一个基于 Streamlit 的多彩种彩票分析网站第二版原型，覆盖：

- 双色球
- 大乐透
- 福彩3D
- 排列3
- 排列5
- 七乐彩
- 快乐8

## 第二版升级结果

这一版相对第一版，已经完成以下重构：

- 从单页应用升级为 Streamlit 多页面结构
- 增加 `pages/`、`services/`、`components/` 分层
- 首页改为产品概览页，不再只是收费表单
- 每个彩种拥有独立分析页面
- 增加会员开通页
- 管理员后台升级为独立页面
- 新增抓取日志、统计缓存、后台操作记录
- 数据更新优先尝试官方源，失败时可回退并记录

## 目录结构

```text
lottery_mvp/
├─ app.py
├─ config.py
├─ db.py
├─ data_service.py
├─ source_fetchers.py
├─ updater.py
├─ pages/
├─ services/
├─ components/
├─ Dockerfile
├─ render.yaml
└─ .github/workflows/daily-update.yml
```

## 本地运行

```bash
pip install -r requirements.txt
python updater.py --seed-demo
streamlit run app.py
```

也可以直接：

```bash
sh start.sh
```

## 默认账号

- 演示访问码：`FREE-DEMO`
- 默认后台密码：`admin123`

上线前建议通过环境变量改掉：

```bash
export ADMIN_PASSWORD='your-password'
export ALLOW_DEMO_FALLBACK='1'
```

## 会员与收费

推荐先用低成本手工模式：

1. 展示微信 / 支付宝收款码
2. 用户付款后提交备注
3. 管理员后台发放访问码，并为 9.9 元月卡勾选 3 个彩种
4. 用户使用访问码登录

当前默认权益：

- 免费版：AI 3 次/天，全部彩种可看基础预览
- 9.9 元月卡：30 天有效，限 3 个彩种，AI 10 次/天

## 自动更新

初始化演示数据：

```bash
python updater.py --seed-demo
```

执行一次更新：

```bash
python updater.py --run-once
```

## 部署建议

### 最低成本验证

- Streamlit Community Cloud
- GitHub Actions 自动更新
- SQLite

### 正式版

- Render Web Service
- Render Cron Job
- PostgreSQL

## Streamlit Cloud 部署路径

如果你的 GitHub 仓库结构保持为：

```text
lottery-mvp/
└─ lottery_mvp/
   ├─ app.py
   ├─ requirements.txt
   └─ pages/
```

那么创建应用时应填写：

- Repository: 你的 GitHub 仓库
- Branch: `main`
- Main file path: `lottery_mvp/app.py`

建议在高级设置里加入：

```text
ADMIN_PASSWORD=你的后台密码
ALLOW_DEMO_FALLBACK=1
```

## Render 部署路径

仓库内已提供 `render.yaml`，适合直接走 Blueprint：

- 一个 PostgreSQL 数据库
- 一个 Web 服务
- 一个 Cron Job

正式环境建议：

- `ALLOW_DEMO_FALLBACK=0`
- 先手动运行一次更新，确认真实抓取是否可达

## 合规定位

本项目定位为：

- 历史开奖查询
- 数据统计与趋势观察
- 娱乐性模拟选号
- AI 辅助解释

不承诺中奖，不提供确定性预测。
