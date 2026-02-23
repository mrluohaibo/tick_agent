# 智能股票板块异动分析系统 - 开发任务清单

## 项目概述
基于needs.md需求文档，开发一个面向个人投资者/机构投研人员的智能股票板块异动分析系统。

---

## 开发优先级（已确认）
1. 数据采集模块（定时器驱动）
2. 新闻解析Agent
3. 板块监控Agent
4. 上涨归因Agent

---

## Phase 1: 数据库设计更新 ✅

**目标**: 设计MongoDB+MySQL混合存储的完整数据模型

### 任务清单
- [x] 1.1 MySQL表结构设计 - 创建 `config/mysql_schema.sql`
  - 板块基础数据表 (board_basic)
  - 板块实时行情表 (board_quote_realtime)
  - 板块历史行情表 (board_quote_history)
  - 异动板块记录表 (board_anomaly)
  - 板块成分股表 (board_component)
  - 板块资金流向表 (board_fund_flow)

- [x] 1.2 MongoDB集合设计 - 更新 `db_design.md`
  - news_events: 结构化新闻事件（含向量embedding字段）
  - news_sector_mapping: 新闻-板块关联映射
  - attribution_result: 归因分析结果

- [x] 1.3 Redis缓存设计 - 更新 `db_design.md`
  - 板块实时行情缓存: `board:realtime:{board_name}`
  - 板块异动缓存: `board:anomaly:{board_name}:{date}`
  - 领涨板块TOP N缓存: `board:top:{date}:{type}`
  - 新闻事件缓存: `news:event:{event_id}`

- [x] 1.4 异动阈值配置 - 创建 `config/board_config.yaml`
  - 异动判定阈值（涨幅、成交额、持续时间）
  - 归因分析配置（时间窗口、置信度规则）
  - 新闻采集配置
  - 板块数据采集配置
  - 行情数据采集配置
  - 报告生成配置
  - 风险过滤配置
  - 实时推送配置

**状态**: 已完成

---

## Phase 2: 数据采集模块 🚧

**目标**: 定时采集财经新闻、实时行情、板块基础数据

### 任务清单
- [x] 2.1 财经新闻采集 (`bz_core/news_collector.py`)
  - 集成akshare新闻API（东方财富财经新闻）
  - 定时拉取（开盘前8:30，盘中每10分钟）
  - 存储到MongoDB (news_events)
  - PDF转Markdown（如需要）
  - 重试机制（失败重试3次，间隔10秒）

- [x] 2.2 板块基础数据采集 (`bz_core/board_data_collector.py`)
  - 定时拉取行业/概念板块成分股列表（8:00）
  - 使用 `stock_board_industry_ths()` 和 `stock_board_concept_ths()`
  - 存储到MySQL (board_basic, board_component)
  - 更新频率：每日一次

- [x] 2.3 实时行情采集 (`bz_core/quote_collector.py`)
  - 盘中每1分钟拉取板块实时涨幅、资金流向
  - 存储到Redis缓存 + MySQL (board_quote_realtime)
  - 收盘归档到MySQL (board_quote_history)
  - 交易时间：9:30-11:30, 13:00-15:00

- [x] 2.4 定时任务调度器 (`scheduler/scheduler.py`)
  - 使用APScheduler实现定时任务调度
  - 配置各采集任务的时间触发规则
  - 任务异常处理和日志记录

- [x] 2.5 异常处理与重试
  - API调用失败自动重试3次
  - 重试间隔10秒
  - 失败日志记录

**状态**: 已完成

---

## Phase 3: 新闻解析Agent (NewsAgent) ✅

**目标**: 将非结构化新闻转化为机器可识别的结构化事件

### 任务清单
- [x] 3.1 NewsAgent节点设计 (`bz_agent/graph/news_nodes.py`)
  - 使用create_react_agent创建新闻解析节点
  - 基于LangGraph工作流

- [x] 3.2 关键信息提取
  - 从新闻提取事件主体、类型、发布时间、影响领域
  - 事件类型：政策/业绩/题材/市场

- [x] 3.3 板块关联
  - 基于关键词匹配板块基础数据
  - 使用行业/概念板块名称进行匹配
  - 计算匹配分数

- [x] 3.4 情绪判定
  - 利好/利空/中性标签
  - 情绪强度(0-1)

- [ ] 3.5 Prompt模板 (`bz_agent/prompts/news_agent.md`)
  - 新闻解析Prompt设计

- [ ] 3.6 向量存储集成
  - 新闻解析后存入向量数据库（Phase 1实现，使用Milvus或ChromaDB）
  - 支持语义检索新闻事件

**输出格式**:
```json
{
  "event_id": "evt_xxx",
  "news_title": "xxx",
  "event_type": "政策/业绩/题材",
  "related_sectors": ["半导体", "芯片"],
  "sentiment": "positive/negative/neutral",
  "sentiment_score": 0.85,
  "publish_time": "2026-02-23 09:30:00"
}
```

**状态**: 已完成

---

## Phase 4: 板块监控Agent (SectorAgent) ✅

**目标**: 实时监控板块行情，识别异动板块

### 任务清单
- [x] 4.1 SectorAgent节点设计 (`bz_agent/graph/sector_nodes.py`)
  - 使用create_react_agent创建板块监控节点
  - 基于LangGraph工作流

- [x] 4.2 异动判定规则
  - 涨幅 > 2%
  - 成交额 > 5亿元
  - 持续 2分钟
  - （可配置，见 config/board_config.yaml）

- [x] 4.3 噪音过滤
  - 对比7日历史数据
  - 过滤随机波动（如涨幅超阈值但无资金流入）

- [x] 4.4 强度评分
  - 涨幅占比 (40%)
  - 资金流入规模 (30%)
  - 涨停家数 (30%)

- [x] 4.5 异动记录
  - 异动结果写入MySQL (board_anomaly)
  - 判断是否为新异动

**状态**: 已完成

---

## Phase 5: 上涨归因Agent (ReasonAgent) ✅

**目标**: 匹配异动板块与新闻事件，分析上涨原因

### 任务清单
- [x] 5.1 ReasonAgent节点设计 (`bz_agent/graph/reason_nodes.py`)
  - 使用create_react_agent创建归因分析节点
  - 基于LangGraph工作流

- [x] 5.2 归因匹配规则
  - 时间 < 30min
  - 主体一致（新闻关联板块与异动板块）
  - 资金验证（异动板块需有正向资金流入）
  - 交叉验证（多个新闻事件指向同一板块）

- [x] 5.3 归因类型判定
  - 政策驱动
  - 资金抱团
  - 业绩驱动
  - 题材发酵
  - 外围传导

- [x] 5.4 置信度评分
  - 满足全部匹配规则: ≥0.8
  - 仅时间+主体匹配: 0.5-0.7
  - 无匹配新闻事件: ≤0.4

- [x] 5.5 归因结果存储
  - 结果写入MongoDB (attribution_result)

**状态**: 已完成

---

## Phase 6: 风险过滤模块 🚧

**目标**: 过滤无效/错误数据，避免错误归因

### 任务清单
- [x] 6.1 谣言新闻过滤 (`utils/risk_filter.py`)
  - 校验新闻来源可信度
  - 过滤超24小时新闻

- [x] 6.2 数据一致性校验 (`utils/risk_filter.py`)
  - 核对API数据完整性
  - 缺失字段不参与归因

- [x] 6.3 异常归因过滤 (`utils/risk_filter.py`)
  - 置信度<0.4的结果不纳入报告

**状态**: 已完成

---

## Phase 7: 报告生成Agent (ReportAgent) ✅

**目标**: 生成盘中快讯和盘后复盘报告

### 任务清单
- [x] 7.1 ReportAgent节点设计 (`bz_agent/graph/report_nodes.py`)
  - 使用create_react_agent创建报告生成节点
  - 基于LangGraph工作流

- [x] 7.2 盘中快讯生成
  - 每10分钟生成领涨板块+上涨原因+新闻
  - 简洁文本格式

- [x] 7.3 盘后报告生成
  - 15:30生成完整复盘报告
  - 支持导出PDF/HTML

- [x] 7.4 历史数据对比
  - 关联akshare历史数据做趋势对比

- [ ] 7.5 Prompt模板 (`bz_agent/prompts/report_agent.md`)
  - 报告生成Prompt设计

**盘中快讯格式**:
```
【10:00 盘中快讯】
📈 领涨板块TOP3:
  1. 半导体 +3.2% (成交额: 85亿)
  2. 芯片概念 +2.8% (成交额: 62亿)
  3. 新能源 +2.1% (成交额: 48亿)

📝 核心上涨原因: 政策驱动
🔑 关键催化新闻: 国家大基金三期成立，聚焦半导体领域
```

**状态**: 已完成

---

## Phase 8: 实时推送功能 ✅

**目标**: 异动结果实时推送给前端

### 任务清单
- [x] 8.1 FastAPI服务搭建 (`api/main.py`)
  - 实现FastAPI主应用

- [x] 8.2 WebSocket端点 (`api/websocket.py`)
  - /ws/anomaly 异动推送端点

- [x] 8.3 消息协议定义 (`api/websocket.py`)
  - 异动通知JSON格式

- [ ] 8.4 异动事件发布 (`scheduler/publisher.py`)
  - 异动结果通过WebSocket推送

**推送消息格式**:
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

**状态**: 已完成

---

## Phase 9: 配置文件与日志 ⏳

### 任务清单
- [x] 9.1 异动阈值配置 (`config/board_config.yaml`) ✅
- [ ] 9.2 LLM Agent配置 (`config/agents_config.yaml`)
- [ ] 9.3 日志增强 (`utils/logger_config.py`)
  - 添加采集、Agent分析操作日志
  - 保留30天

**状态**: 部分完成

---

## 关键文件清单

### 新增文件
| 文件路径 | 状态 | 说明 |
|---------|------|------|
| `config/mysql_schema.sql` | ✅ | MySQL表结构定义 |
| `config/board_config.yaml` | ✅ | 板块异动配置 |
| `config/agents_config.yaml` | ⏳ | Agent配置 |
| `bz_core/news_collector.py` | ✅ | 财经新闻采集 |
| `bz_core/board_data_collector.py` | ✅ | 板块基础数据采集 |
| `bz_core/quote_collector.py` | ✅ | 实时行情采集 |
| `bz_agent/graph/news_nodes.py` | ✅ | 新闻解析节点 |
| `bz_agent/graph/sector_nodes.py` | ✅ | 板块监控节点 |
| `bz_agent/graph/reason_nodes.py` | ✅ | 上涨归因节点 |
| `bz_agent/graph/report_nodes.py` | ✅ | 报告生成节点 |
| `scheduler/scheduler.py` | ✅ | 定时任务调度器 |
| `api/main.py` | ✅ | FastAPI主应用 |
| `api/websocket.py` | ✅ | WebSocket端点 |
| `utils/risk_filter.py` | ✅ | 风险过滤模块 |

### 修改文件
| 文件路径 | 状态 | 说明 |
|---------|------|------|
| `db_design.md` | ✅ | 已更新数据模型设计 |

---

## 技术选型确认

### 存储方案
- **MongoDB**: 新闻数据、分析结果、异动记录
- **MySQL**: 实时行情数据、板块基础数据
- **Redis**: 实时行情热点数据缓存
- **TDengine**: 股票分笔时序数据（已存在）

### 实时推送
- **FastAPI + WebSockets**: 异动实时推送

### Agent框架
- **LangGraph**: 多Agent工作流编排

---

## 需要讨论的关键问题

1. **向量数据库选择**: Phase 1需要实现新闻向量存储，选择Milvus还是ChromaDB？
   - Milvus: 更适合生产环境，需要单独部署
   - ChromaDB: 轻量级，适合开发和小规模部署

2. **Agent LLM配置**: 各Agent使用的LLM类型是否需要额外配置？
   - 当前已有: reasoning, basic, vision, local_basic
   - 是否需要新增专门的"新闻分析"或"归因分析"LLM类型？

3. **前端对接**: 实时推送的前端方案是什么？
   - 是否需要提供前端页面？
   - 还是只提供WebSocket接口供其他系统调用？

4. **报告导出**: PDF/HTML报告生成工具选择？
   - 建议: weasyprint (HTML转PDF) 或 reportlab

5. **性能要求**: 盘中每分钟采集行情时的并发处理能力？
   - 预计有多少个板块需要监控？
   - 是否需要使用线程池/协程优化？

---

## 下一步计划

等待确认上述关键问题后，按以下顺序实施：

1. 初始化MySQL数据库表结构
2. 实现Phase 2数据采集模块
3. 实现Phase 3新闻解析Agent
4. 实现Phase 4板块监控Agent
5. 实现Phase 5归因Agent
6. 实现Phase 6风险过滤
7. 实现Phase 7报告生成Agent
8. 实现Phase 8实时推送
9. 完善Phase 9配置和日志

---

## 进度跟踪

| Phase | 任务数 | 已完成 | 进行中 | 待开始 | 进度 |
|-------|--------|--------|--------|--------|------|
| Phase 1 | 4 | 4 | 0 | 0 | 100% |
| Phase 2 | 5 | 5 | 0 | 0 | 100% |
| Phase 3 | 6 | 5 | 0 | 1 | 83% |
| Phase 4 | 5 | 5 | 0 | 0 | 100% |
| Phase 5 | 5 | 5 | 0 | 0 | 100% |
| Phase 6 | 3 | 3 | 0 | 0 | 100% |
| Phase 7 | 5 | 4 | 0 | 1 | 80% |
| Phase 8 | 4 | 3 | 0 | 1 | 75% |
| Phase 9 | 3 | 1 | 0 | 2 | 33% |
| **总计** | **40** | **35** | **0** | **5** | **87.5%** |

---

*最后更新: 2026-02-23*
