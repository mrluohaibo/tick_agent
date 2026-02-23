# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a stock information and news aggregation system with multi-agent AI capabilities. The project consists of:
- **bz_core**: Core stock data fetching and storage using akshare/baostock APIs
- **bz_agent**: LangGraph-based multi-agent system with ReAct pattern for web browsing and content extraction
- **bz_orm**: Database ORM utilities
- **utils**: Shared utilities for logging, database connections, date handling, etc.

## Development Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install Playwright Browsers
```bash
playwright install
```

### Run Main Application
```bash
python main.py
```

### Run Agent Workflow (for web content extraction)
```bash
python bz_agent/workflow.py
```

### Run Native URL to Markdown Agent
```bash
python bz_agent/native_agent/native_url_to_markdown_agent.py
```

### Run Tests
```bash
python -m pytest tests/
# Run specific test
python -m pytest tests/test_module.py
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

### Start Local LLM (Optional)
```bash
# Using Ollama
ollama run qwen3

# Using vLLM
python -m vllm.entrypoints.openai.api_server --model F:/python_pro/tick_info/model/Qwen3-0.6B --dtype auto --port 8000
```

## Architecture

### Multi-Agent System (bz_agent)

The project uses **LangGraph** for building stateful agent workflows. The workflow consists of:

1. **Planner Node** (`planner_node`): Generates a full plan using reasoning LLM (qwen/qwq-plus)
2. **Supervisor Node** (`supervisor_node`): Routes tasks to appropriate workers
3. **Worker Agents**:
   - `coder_agent`: Python code execution with python_repl_tool and bash_tool
   - `browser_agent`: Web browsing with browser_tool
   - `url_to_markdown_agent`: Extracts markdown content from URLs
   - `reporter_agent`: Writes final reports

The workflow flow: `START -> planner -> supervisor -> (coder/browser/url_to_markdown) -> supervisor -> ... -> END`

See `bz_agent/graph/builder.py` for graph structure and `bz_agent/workflow.py` for workflow execution.

### Native ReAct Agent (bz_agent/native_agent)

Alternative agent implementation with custom ReAct pattern:
- **BaseAgent**: Abstract base for agent state management and execution loop
- **ReActAgent**: Think-Act pattern with think() and act() methods
- **ToolCallAgent**: Uses OpenAI-style tool calling with ToolCollection

See `bz_agent/native_agent/react.py` and `bz_agent/native_agent/toolcall.py`.

### LLM Configuration

LLM types are defined in `bz_agent/config/agents_map.py`:
- `reasoning`: Complex reasoning tasks (planner) - uses qwq-plus via Aliyun
- `basic`: General tasks - uses qwen-max-latest via Aliyun
- `vision`: Visual tasks (browser) - uses qwen2.5-vl-72b-instruct
- `local_basic`: Local development - uses Ollama qwen3:4b

Environment variables are loaded from `config/llm.env`. Modify this file for different LLM providers.

### Stock Data Pipeline (bz_core)

**StockInfo** class (`bz_core/stock_info_api.py`) handles:
- Real-time stock data fetching from akshare
- Historical K-line data from baostock
- Stock tick data storage in TDengine
- Stock business/intro information
- MongoDB for metadata, TDengine for time-series tick data

Key methods:
- `get_all_stock_info()`: Fetch all A-share stock data
- `query_all_stock_history_k_daily_data()`: Fetch historical K-line for all stocks
- `query_stock_tick_store_db()`: Fetch and store tick data to TDengine
- `query_stock_intro()`: Fetch stock business introduction

### Database Configuration

All database configs in `config/application.yaml`:
- **MongoDB**: Stock metadata and history (host: 192.168.99.108:27017)
- **MySQL**: Transactional data (host: 192.168.99.108:3306)
- **Redis**: Caching (host: 192.168.99.108:6379)
- **TDengine**: Time-series stock tick data (host: 192.168.99.108:6030)

Database clients are initialized in `utils/db_tool_init.py` and available as module-level variables:
- `mongo_client`, `mysql_client`, `redis_client`, `td_engine_client`

### Tools

Agent tools are defined in `bz_agent/tools/`:
- `browser_tool`: Playwright-based web automation
- `python_repl_tool`: Python code execution
- `bash_tool`: Shell command execution
- `page_html_tool`: HTML content extraction

## Important Notes

### Chinese Field Mapping
Stock data uses Chinese-to-English field mappings in `bz_core/stock_dict.py`. When adding new fields, update these dictionaries:
- `stock_dict_zh_2_en`: Basic stock info fields
- `stock_tick_dict`: Tick data fields
- `stock_intro_dict`: Stock intro fields

### Configuration Loading
- Application config: `config/application.yaml` loaded via `utils.config_init.application_conf`
- LLM config: `config/llm.env` loaded via `python-dotenv` in `bz_agent/config/init_config.py`
- Root path is defined in `bz_core.Constant.root_path`

### Pre-commit Hooks
Enforces code quality:
- Ruff linting and formatting
- YAML validation
- Conventional commit messages

### Thread Pool
`bz_core/thread_pool_define.py` defines `handle_daily_stock_data_pool` for concurrent stock data processing.

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point for stock data operations |
| `bz_agent/workflow.py` | Multi-agent workflow orchestration |
| `bz_agent/graph/builder.py` | LangGraph workflow definition |
| `bz_core/stock_info_api.py` | Stock data fetching and storage |
| `config/application.yaml` | Database configuration |
| `config/llm.env` | LLM API keys and endpoints |
