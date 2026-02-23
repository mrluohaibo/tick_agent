# 智能股票板块异动分析系统

> 基于多Agent智能分析 + 实时数据采集的A股板块异动监控系统

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 项目简介

本系统是一个面向个人投资者/机构投研人员的智能股票板块异动分析工具。核心功能包括：

- **实时监控**: 盘中实时监控板块行情，自动识别异动板块
- **智能归因**: 基于财经新闻和板块数据，智能分析板块上涨原因
- **自动报告**: 生成盘中快讯和盘后复盘报告
- **实时推送**: 异动结果通过WebSocket实时推送到前端

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    APScheduler 定时任务调度器                 │
│  08:00 板块基础数据   08:30 盘前新闻                │
│  盘中每1分钟实时行情   15:30 盘后归档                │
└──────────────────┬──────────────────────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
       ▼           ▼           ▼
  ┌─────┐   ┌─────┐   ┌─────┐
  │新闻  │   │行情  │   │板块  │
  │采集  │   │采集  │   │基础  │
  └───┬─┘   └───┬─┘   └───┬─┘
      │           │           │
      └───────────┴───────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │   多存储架构       │
        ├─ MySQL (行情/基础)│
        ├─ MongoDB (新闻/分析)│
        ├─ Redis (缓存)      │
        └─ TDengine (分笔)   │
        └─────────────────────┘
                  │
      ┌───────────────────────┼──────────────────────┐
      │                       │
      ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ LangGraph Agents │─────▶│  风险过滤模块     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
            ┌─────────────────────┐
            │   报告生成Agent     │
            └──────────┬──────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
    ┌──────────┐         ┌──────────┐
    │  报告    │         │WebSocket  │
    │  文件    │         │  推送     │
    └──────────┘         └──────────┘
```

## 功能特性

### 数据采集模块

| 功能 | 说明 | 调度 |
|------|------|------|
| 财经新闻采集 | 东方财富新闻 + PDF转Markdown | 08:30 / 盘中每10分钟 |
| 板块基础数据采集 | 行业/概念板块成分股列表 | 08:00 每日 |
| 实时行情采集 | 板块实时涨幅、资金流向、量比 | 盘中每1分钟 |
| 行情归档 | 收盘行情归档到历史表 | 15:30 |

### 多Agent智能分析

| Agent | 功能 | LLM类型 |
|--------|------|----------|
| NewsAgent | 新闻解析：事件提取、板块关联、情绪判定 | basic |
| SectorAgent | 板块监控：异动检测、噪音过滤、强度评分 | basic |
| ReasonAgent | 上涨归因：新闻匹配、归因类型判定、置信度评分 | reasoning |
| ReportAgent | 报告生成：盘中快讯、盘后复盘报告 | basic |

### 异动判定规则

- **涨幅阈值**: 板块涨幅 > 2%（可配置）
- **成交额阈值**: 板块成交额 > 5亿元（可配置）
- **持续判定**: 涨幅连续维持2分钟以上（可配置）
- **噪音过滤**: 对比7日历史数据，过滤随机波动

### 归因类型

| 类型 | 说明 |
|------|------|
| 政策驱动 | 政府政策、法规变化等宏观因素 |
| 资金抱团 | 大资金集中流入某板块 |
| 业绩驱动 | 上市公司业绩超预期或重大事件 |
| 题材发酵 | 市场热点话题或概念炒作 |
| 外围传导 | 外围市场或国际形势传导 |

### 风险过滤

- **新闻来源验证**: 只保留可信来源的新闻
- **新闻时效过滤**: 超过24小时的新闻不参与分析
- **数据完整性校验**: 缺失关键字段的数据不参与归因
- **低置信度过滤**: 置信度 < 0.4 的归因结果不纳入报告

## 技术栈

### 核心技术

- **Python 3.8+**: 主要开发语言
- **LangGraph**: 多Agent工作流编排
- **APScheduler**: 定时任务调度
- **FastAPI**: Web API框架
- **WebSockets**: 实时消息推送

### 数据库

| 数据库 | 用途 | 集合/表 |
|--------|------|---------|
| MongoDB | 新闻、分析结果 | news_events, news_sector_mapping, attribution_result |
| MySQL | 行情、基础数据 | board_basic, board_quote_realtime, board_quote_history, board_anomaly |
| Redis | 实时缓存 | board:realtime:*, board:anomaly:* |
| TDengine | 分笔时序数据 | stock_tick |

### 数据源

- **akshare**: 财经新闻、实时行情、板块数据
- **东方财富**: 行业/概念板块数据
- **巨潮资讯**: 公告数据

## 项目结构

```
tick_info/
├── api/                      # API服务
│   ├── main.py               # FastAPI主应用
│   └── websocket.py           # WebSocket管理
│
├── bz_agent/                 # 多Agent系统
│   ├── config/               # Agent配置
│   ├── graph/                # LangGraph图定义
│   │   ├── builder.py        # 工作流构建器
│   │   ├── types.py          # 状态类型
│   │   ├── nodes.py          # 节点实现
│   │   ├── news_nodes.py     # 新闻解析节点
│   │   ├── sector_nodes.py   # 板块监控节点
│   │   ├── reason_nodes.py   # 归因节点
│   │   └── report_nodes.py   # 报告节点
│   └── prompts/             # Prompt模板
│       ├── news_agent.md
│       └── report_agent.md
│
├── bz_core/                  # 核心数据采集
│   ├── news_collector.py      # 新闻采集
│   ├── board_data_collector.py # 板块数据采集
│   ├── quote_collector.py     # 实时行情采集
│   ├── stock_info_api.py     # 股票数据API
│   └── stock_news_info_api.py # 新闻API
│
├── config/                   # 配置文件
│   ├── application.yaml       # 应用配置（数据库）
│   ├── board_config.yaml      # 板块异动配置
│   ├── agents_config.yaml     # Agent配置
│   ├── llm.env              # LLM密钥
│   └── mysql_schema.sql      # MySQL表结构
│
├── my_akshare/              # akshare封装
│   ├── news/                # 新闻接口
│   ├── stock/               # 股票接口
│   ├── stock_a/             # A股接口
│   └── ...
│
├── scheduler/                # 定时任务
│   └── scheduler.py         # APScheduler调度器
│
├── utils/                    # 工具类
│   ├── db_tool_init.py       # 数据库初始化
│   ├── logger_config.py      # 日志配置
│   ├── mongo_util.py        # MongoDB工具
│   ├── mysql_client.py       # MySQL客户端
│   ├── redis_client.py       # Redis客户端
│   └── risk_filter.py       # 风险过滤
│
└── reports/                  # 报告输出目录
    └── *.txt, *.html
```

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone <repository-url>
cd tick_info

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器（如使用browser_agent）
playwright install
```

### 2. 配置设置

编辑 `config/llm.env` 配置LLM密钥：
```bash
# 阿里云API配置（示例）
DASHSCOPE_API_KEY=your_api_key_here
```

编辑 `config/application.yaml` 配置数据库连接：
```yaml
mysql:
  host: 'your_mysql_host'
  port: 3306
  user: 'your_user'
  password: 'your_password'
  database: 'stock_info'
```

### 3. 初始化数据库

```bash
# 初始化MySQL表结构
mysql -h 192.168.99.108 -u root -p stock_info < config/mysql_schema.sql
```

### 4. 启动服务

```bash
# 启动定时任务调度器（数据采集）
python scheduler/scheduler.py

# 启动FastAPI服务（API + WebSocket）
python api/main.py
```

服务启动后：
- API服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws/anomaly

### 5. 验证安装

```bash
# 测试新闻采集
python bz_core/news_collector.py

# 测试板块数据采集
python bz_core/board_data_collector.py

# 测试实时行情采集
python bz_core/quote_collector.py

# 测试风险过滤
python utils/risk_filter.py

# 测试日志配置
python utils/logger_config.py
```

## API接口

### 健康检查
```http
GET /health
```

### 板块数据
```http
GET /api/boards/top?limit=10
# 响应
{
  "status": "success",
  "data": {
    "boards": [...],
    "limit": 10
  }
}
```

### 异动数据
```http
GET /api/anomalies?limit=20
# 响应
{
  "status": "success",
  "data": {
    "anomalies": [...],
    "count": 20
  }
}
```

### 归因查询
```http
GET /api/attribution/{board_name}?hours=24
# 响应
{
  "status": "success",
  "data": {
    "board_name": "半导体",
    "attribution": {...},
    "count": 1
  }
}
```

### 任务触发

```http
POST /api/tasks/news_analysis
# 触发新闻分析任务

POST /api/tasks/sector_monitor
# 触发板块监控任务

POST /api/tasks/attribution
# 触发归因分析任务

POST /api/tasks/report
# 生成报告
# body: {"type": "intraday" | "post_market"}
```

### WebSocket推送

连接URL: `ws://localhost:8000/ws/anomaly`

消息格式：
```json
{
  "type": "anomaly_alert",
  "data": {
    "board_name": "半导体",
    "change_rate": 3.2,
    "reason": "政策驱动",
    "news_title": "国家大基金三期成立",
    "confidence": 0.85,
    "trigger_time": "2026-02-23 10:30:00"
  },
  "timestamp": "2026-02-23 10:30:05"
}
```

## 配置说明

### 板块异动配置 (config/board_config.yaml)

```yaml
anomaly:
  change_rate_threshold: 2.0      # 涨幅阈值(%)
  turnover_threshold: 500000000    # 成交额阈值(元)
  duration_threshold: 2            # 持续时间(分钟)
  volume_ratio_threshold: 1.5       # 量比阈值

attribution:
  time_match_window: 30            # 归因时间窗口(分钟)
  confidence:
    high_threshold: 0.8
    medium_threshold: 0.5
    low_threshold: 0.4
```

### Agent配置 (config/agents_config.yaml)

```yaml
agent_llm_map:
  news_agent: "basic"
  sector_agent: "basic"
  reason_agent: "reasoning"
  report_agent: "basic"

agents:
  news_agent:
    temperature: 0.3
    max_tokens: 2000
```

## 日志管理

日志文件存储在 `logs/` 目录，按模块分类：

- `app_YYYY-MM-DD.log` - 应用主日志
- `data_collection_YYYY-MM-DD.log` - 数据采集日志
- `agent_news_YYYY-MM-DD.log` - 新闻Agent日志
- `agent_sector_YYYY-MM-DD.log` - 板块Agent日志
- `agent_reason_YYYY-MM-DD.log` - 归因Agent日志
- `agent_report_YYYY-MM-DD.log` - 报告Agent日志
- `websocket_YYYY-MM-DD.log` - WebSocket日志

日志保留策略：30天自动清理

## 开发指南

### 代码规范

项目使用 `ruff` 进行代码格式化和检查：

```bash
# 运行linter（自动修复）
ruff check --fix

# 运行formatter
ruff format
```

### 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_module.py
```

### Pre-commit Hooks

安装pre-commit钩子：
```bash
pre-commit install
```

## 部署说明

### Docker部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "scheduler/scheduler.py"]
```

```bash
# 构建镜像
docker build -t stock-analysis-system .

# 运行调度器
docker run -d stock-analysis-system python scheduler/scheduler.py

# 运行API服务
docker run -d -p 8000:8000 stock-analysis-system python api/main.py
```

### 生产环境配置

1. 修改 `config/application.yaml` 中的数据库连接为生产环境
2. 配置 `config/llm.env` 中的API密钥
3. 使用 `supervisor` 或 `systemd` 管理进程

## 常见问题

### Q: 数据采集失败？
A: 检查网络连接和akshare接口可用性，查看日志中的重试记录。

### Q: Agent分析结果不准确？
A: 调整 `config/agents_config.yaml` 中的temperature参数，降低temperature使输出更稳定。

### Q: WebSocket连接断开？
A: 检查防火墙设置，确保8000端口开放。

### Q: 如何调整异动阈值？
A: 编辑 `config/board_config.yaml` 中的anomaly配置，无需修改代码。

## 相关文档

- [需求文档 (needs.md)](needs.md)
- [数据库设计 (db_design.md)](db_design.md)
- [开发任务 (todo.md)](todo.md)
- [配置文件 (config/)](config/)

## 许可证

MIT License

