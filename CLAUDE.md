# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an intelligent stock sector anomaly analysis system with multi-agent AI capabilities. The project consists of:

- **bz_core**: Core stock data fetching and storage using akshare/baostock APIs
- **bz_agent**: LangGraph-based multi-agent system for news parsing, sector monitoring, attribution analysis, and report generation
- **scheduler**: APScheduler-based task scheduling for data collection
- **api**: FastAPI service with WebSocket for real-time anomaly notifications
- **utils**: Shared utilities for logging, database connections, risk filtering, etc.

## Development Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Code Formatting and Linting
```bash
# Run ruff linter (auto-fixes)
ruff check --fix

# Run ruff formatter
ruff format
```

### Install Pre-commit Hooks
```bash
pre-commit install
```

### Initialize Database
```bash
# Create MySQL tables
mysql -h 192.168.99.108 -u root -p stock_info < config/mysql_schema.sql
```

### Run Data Collection Tests
```bash
# Test news collector
python bz_core/news_collector.py

# Test board data collector
python bz_core/board_data_collector.py

# Test quote collector
python bz_core/quote_collector.py
```

### Run Agent Tests
```bash
# Test news parsing agent
python bz_agent/graph/news_nodes.py

# Test sector monitoring agent
python bz_agent/graph/sector_nodes.py

# Test attribution agent
python bz_agent/graph/reason_nodes.py

# Test report agent
python bz_agent/graph/report_nodes.py

# Test risk filter
python utils/risk_filter.py

# Test logger config
python utils/logger_config.py
```

### Start Scheduler
```bash
# Start APScheduler for data collection
python scheduler/scheduler.py
```

### Start API Service
```bash
# Start FastAPI with WebSocket support
python api/main.py
```

### Run Stock Data Operations
```bash
# Run main stock info operations
python main.py
```

## Architecture

### Data Collection Pipeline

The data collection module uses APScheduler to drive data fetching:

```
┌─────────────────────────────────────────────┐
│         APScheduler (scheduler)          │
│  08:00 - Board basic data             │
│  08:30 - Pre-market news              │
│  09:30-15:00 - Real-time quotes (1min)  │
│  15:30 - Market close archive           │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼
┌─────────┐ ┌──────────┐ ┌──────────────┐
│  News    │ │  Board    │ │    Quote     │
│Collector│ │  Collector│ │   Collector   │
└────┬────┘ └────┬─────┘ └──────┬─────────┘
     │             │              │
     └─────────────┴──────────────┘
                  │
                  ▼
        ┌──────────────────────┐
        │   Multi-Storage      │
        ├─ MySQL (quotes)     │
        ├─ MongoDB (news/analysis)
        ├─ Redis (cache)      │
        └─ TDengine (ticks)    │
        └──────────────────────┘
```

### Multi-Agent System (bz_agent)

The project uses LangGraph for building stateful agent workflows. The intelligent sector analysis system introduces new agents for anomaly detection and attribution:

```
┌──────────────────────────────────────────────────────────┐
│         LangGraph Workflow Builder                     │
│         StateGraph(State) + START                │
│                  ↓                                │
└──────────────────┬───────────────────────────────┘
                   │
    ┌─────────────────────────────┼──────────────────┐
    │                         │
    ▼                         ▼
┌─────────────┐      ┌──────────────────────┐
│  New Nodes  │──────▶│  Core Nodes          │
└──────┬────┘      │  (from original)     │
       │             │                       │
┌──────┼────────────┼────────────────────────┐
│News │Sector │Reason │Report (orig)     │
│Agent │ Agent │ Agent  │   Agent           │
└───┬─┘  └───┬─┘  └──────┬───────────┘
    │          │          │        │
    └──────────┴──────────┴────────┴────────┘
               │
               ▼
    ┌───────────────────────┐
    │  Risk Filter Module  │
    │  (utils/risk_filter)│
    └──────────┬───────────┘
               │
               ▼
        ┌─────────────────────┐
        │   Report Agent       │
        │   (New)            │
        └──────────┬───────────┘
                   │
        ┌───────────┴─────────┐
        │                        │
        ▼                        ▼
   ┌──────────┐         ┌──────────────┐
   │ Reports  │         │  WebSocket     │
   │          │         │  Push          │
   └──────────┘         └──────────────┘
```

### New Agent Nodes (Sector Analysis)

- **news_nodes.py**: NewsAnalysisAgent - Parses financial news, extracts event types, sentiment, and sector associations
- **sector_nodes.py**: SectorMonitorAgent - Monitors board quotes, detects anomalies, filters noise, calculates strength scores
- **reason_nodes.py**: AttributionAgent - Matches anomaly boards with news, performs attribution analysis with confidence scoring
- **report_nodes.py**: ReportAgent - Generates intraday alerts and post-market reports

### Core Agent Nodes (Existing)

- **planner_node**: Generates full plan using reasoning LLM (qwq-plus)
- **supervisor_node**: Routes tasks to appropriate workers
- **code_node**: Python code execution with python_repl_tool and bash_tool
- **browser_node**: Web browsing with browser_tool
- **url_to_markdown_node**: Extracts markdown content from URLs
- **reporter_node**: Writes final reports

## LLM Configuration

LLM types are defined in `bz_agent/config/agents_map.py`:

| Type | Usage |
|------|--------|
| `reasoning` | Complex reasoning tasks (planner, attribution analysis) |
| `basic` | General tasks (data validation, simple analysis) |
| `vision` | Visual tasks (browser operations) |
| `local_basic` | Local development (Ollama qwen3) |

Environment variables are loaded from `config/llm.env`. Modify this file for different LLM providers.

Agent-LLM mapping is in `config/agents_config.yaml`:

- **news_agent**: basic (temperature: 0.3)
- **sector_agent**: basic (temperature: 0.1)
- **reason_agent**: reasoning (temperature: 0.5)
- **report_agent**: basic (temperature: 0.7)

## Database Configuration

All database configs are in `config/application.yaml`:

| Database | Host | Port | Database | Usage |
|----------|------|------|----------|--------|
| MongoDB | 192.168.99.108 | 27017 | stock_db | Stock metadata, K-line, business intro |
| TDengine | 192.168.99.108 | 6030 | stock_tick_info | Stock tick time-series data |
| MySQL | 192.168.99.108 | 3306 | stock_info | Board quotes, basic data, anomalies |
| Redis | 192.168.99.108 | 6379 | 0 | Real-time cache |

**Database Schema**: See `config/mysql_schema.sql` for table definitions.

**Client Initialization**: All database clients are initialized in `utils/db_tool_init.py`:
- `mongo_client`: MongoManager instance
- `mysql_client`: TransactionalMySQLClient instance
- `redis_client`: RedisClient instance
- `td_engine_client`: TDEngineClient instance

## Board Anomaly Configuration

Board anomaly configuration is in `config/board_config.yaml`:

**Anomaly Detection**:
- `change_rate_threshold`: 2.0 (板块涨幅阈值%)
- `turnover_threshold`: 500000000 (成交额阈值元)
- `duration_threshold`: 2 (持续分钟数)
- `volume_ratio_threshold`: 1.5 (量比阈值)

**Attribution**:
- `time_match_window`: 30 (归因时间窗口分钟)
- `attribution_types`: policy/fund/earnings/topic/external

**Risk Filtering**:
- `max_news_age_hours`: 24 (最大新闻时效)
- `min_confidence`: 0.4 (最低置信度阈值)

## Data Source Integration

The project integrates akshare via `my_akshare/`:

**News APIs** (from `my_akshare/news/`):
- `news_stock_em`: 东方财富个股新闻

**Stock APIs** (from `my_akshare/stock/`):
- `stock_board_industry_em`: 行业板块实时行情
- `stock_board_concept_name_em`: 概念板块名称和行情

**Fund Flow APIs** (from `my_akshare/stock_a/`):
- `stock_individual_fund_flow_rank`:  个股/板块资金流向排名

## Key Files for Sector Analysis

| File | Purpose |
|------|---------|
| `bz_core/news_collector.py` | Financial news collection with MongoDB storage |
| `bz_core/board_data_collector.py` | Board basic data and component collection |
| `bz_core/quote_collector.py` | Real-time quote collection with Redis cache + MySQL |
| `scheduler/scheduler.py` | APScheduler-based task scheduling |
| `bz_agent/graph/news_nodes.py` | News parsing agent with LLM analysis |
| `bz_agent/graph/sector_nodes.py` | Sector monitoring agent with anomaly detection |
| `bz_agent/graph/reason_nodes.py` | Attribution agent with confidence scoring |
| `bz_agent/graph/report_nodes.py` | Report generation agent |
| `utils/risk_filter.py` | Risk filtering for news, data, and attribution |
| `api/main.py` | FastAPI application with WebSocket endpoint |
| `api/websocket.py` | WebSocket connection management |
| `config/board_config.yaml` | Board anomaly configuration |
| `config/agents_config.yaml` | Agent LLM and behavior configuration |
| `config/mysql_schema.sql` | MySQL table schema definitions |
| `bz_agent/prompts/news_agent.md` | News analysis prompt template |
| `bz_agent/prompts/report_agent.md` | Report generation prompt template |

## Important Notes

### Chinese Field Mapping
Stock data uses Chinese-to-English field mappings in `bz_core/stock_dict.py`. When adding new fields, update these dictionaries:
- `stock_dict_zh_2_en`: Basic stock info fields
- `stock_tick_dict`: Tick data fields
- `stock_intro_dict`: Stock intro fields

### Configuration Loading
- Application config: `config/application.yaml` loaded via `utils.config_init.application_conf`
- LLM config: `config/llm.env` loaded via `python-dotenv` in `bz_agent/config/init_config.py`
- Board config: `config/board_config.yaml` loaded via `application_conf`
- Agent config: `config/agents_config.yaml` loaded via `application_conf`
- Root path is defined in `bz_core.Constant.root_path`

### Pre-commit Hooks
Enforces code quality:
- Ruff linting and formatting
- YAML validation
- Conventional commit messages

### Thread Pool
`bz_core/thread_pool_define.py` defines `handle_daily_stock_data_pool` for concurrent stock data processing.

### Logging
Enhanced logging in `utils/logger_config.py`:
- Multiple module loggers: app, data_collection, agent_news, agent_sector, agent_reason, agent_report, websocket
- 30-day retention with rotating file handler
- Helper functions: `log_agent_operation`, `log_llm_request`, `log_data_collection`

## FastAPI and WebSocket

**API Server**: Run with `python api/main.py`
- Default host: 0.0.0.0, port: 8000
- API docs: http://localhost:8000/docs

**WebSocket**: `ws://localhost:8000/ws/anomaly`
- Connection management in `api/websocket.py`
- Message types: anomaly_alert, attribution_result, intraday_alert
- Message format defined in protocol classes

## Initialization Script

All database clients are initialized in `utils/db_tool_init.py`:

```python
mysql_client = init_mysql()
mongo_client = init_mongo_db()
redis_client = init_redis()
td_engine_client = init_td_engine_client()
```

Use these directly in other modules after import.

## Agent Workflow for Sector Analysis

The sector analysis workflow runs through these stages:

1. **Data Collection**: Scheduler collects news, board data, and quotes
2. **News Parsing**: NewsAgent analyzes news structure, sentiment, and sector associations
3. **Anomaly Detection**: SectorAgent detects anomalous boards based on thresholds
4. **Risk Filtering**: Filters out invalid news and data
5. **Attribution Analysis**: ReasonAgent matches anomalies with news, performs attribution with confidence
6. **Report Generation**: ReportAgent generates intraday alerts and post-market reports
7. **Real-time Push**: WebSocket broadcasts anomaly alerts to connected clients
