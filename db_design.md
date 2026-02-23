# 数据库设计文档

## 概述

本项目使用多数据库架构，根据数据特性和访问模式选择合适的存储方案：
- **MongoDB**: 存储股票元数据、历史K线数据、业务介绍等结构化/半结构化数据
- **TDengine**: 存储高频股票分笔数据（时序数据）
- **MySQL**: 事务性数据（预留）
- **Redis**: 缓存层（预留）

## 数据库连接配置

| 数据库 | 主机 | 端口 | 数据库名称 | 用途 |
|--------|------|------|-----------|------|
| MongoDB | 192.168.99.108 | 27017 | stock_db | 股票元数据、K线数据、业务介绍 |
| TDengine | 192.168.99.108 | 6030 | stock_tick_info | 股票分笔时序数据 |
| MySQL | 192.168.99.108 | 3306 | stock_info | 事务性数据 |
| Redis | 192.168.99.108 | 6379 | 0 | 缓存层 |

---

## MongoDB 数据模型

### 1. 股票基本信息表 (Collection: `all_stock_basic`)

存储所有A股股票的实时基本信息。

**字段映射** (来自 `bz_core/stock_dict.py:stock_dict_zh_2_en`):

| 中文名称 | 英文字段名 | 类型 | 说明 |
|---------|-----------|------|------|
| 代码 | stock_code | String | 股票代码（主键） |
| 名称 | stock_name | String | 股票名称 |
| 最新价 | new_quota | Float | 最新价格 |
| 涨跌幅 | price_change | Float | 涨跌幅百分比 |
| 涨跌额 | price_change_amount | Float | 涨跌金额 |
| 成交量 | trading_volume | Long | 成交量 |
| 成交额 | transaction_volume | Float | 成交额 |
| 振幅 | amplitude | Float | 振幅 |
| 最高 | highest | Float | 最高价 |
| 最低 | lowest | Float | 最低价 |
| 今开 | today_open | Float | 今日开盘价 |
| 昨收 | yesterday_close | Float | 昨日收盘价 |
| 量比 | volume_ratio | Float | 量比 |
| 换手率 | turnover_rate | Float | 换手率 |
| 市盈率-动态 | pe_dynamic | Float | 动态市盈率 |
| 市净率 | price-to-book_ratio | Float | 市净率 |
| 总市值 | total_market_capitalization | Float | 总市值 |
| 流通市值 | market_capitalization | Float | 流通市值 |
| 涨速 | rate_of_increase | Float | 涨速 |
| 5分钟涨跌 | 5-minute_price_fluctuation | Float | 5分钟涨跌 |
| 60日涨跌幅 | 60-day_price_change | Float | 60日涨跌幅 |
| 年初至今涨跌幅 | year-to-date_price_change | Float | 年初至今涨跌幅 |
| 行业 | industry | String | 所属行业 |
| 上市时间 | launch_date | String | 上市日期 |
| 总股本 | total_share_capital | Long | 总股本 |
| 流通股 | floating_shares | Long | 流通股本 |
| create_time | create_time | String | 创建时间 |
| update_time | update_time | String | 更新时间 |

**索引**:
- `stock_code`: 唯一索引
- `update_time`: 用于查询最新更新

**操作方法**: `StockInfo.get_all_stock_info()`, `StockInfo.insert_stock_info_2_mongo()`

---

### 2. 股票日K线历史数据表 (Collection: `stock_daily_k_history`)

存储每只股票的历史日K线数据，来源于 baostock。

**字段结构**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| stock_code | String | 股票代码（与 all_stock_basic 关联） |
| date | String | 交易日期 (YYYY-MM-DD) |
| code | String | 标准化代码 (如 sh.600000) |
| open | Float | 开盘价 |
| high | Float | 最高价 |
| low | Float | 最低价 |
| close | Float | 收盘价 |
| preclose | Float | 前收盘价 |
| volume | Float | 成交量 |
| amount | Float | 成交额 |
| adjustflag | String | 复权类型 |
| turn | Float | 换手率 |
| tradestatus | String | 交易状态 |
| pctChg | Float | 涨跌幅 |
| isST | String | 是否ST |

**索引**:
- `stock_code`, `date`: 联合唯一索引

**操作方法**: `StockInfo.query_history_key_data()`, `StockInfo.save_history_k_daily_data_to_mongo()`

---

### 3. 股票业务介绍表 (Collection: `stock_business_intro`)

存储股票的主营业务、产品类型等介绍信息。

**字段映射** (来自 `bz_core/stock_dict.py:stock_intro_dict`):

| 中文名称 | 英文字段名 | 类型 | 说明 |
|---------|-----------|------|------|
| 代码 | stock_code | String | 股票代码（主键） |
| 主营业务 | primary_business | String | 主营业务描述 |
| 产品类型 | product_type | String | 产品类型 |
| 产品名称 | product_name | String | 产品名称 |
| 经营范围 | business_scope | String | 经营范围 |

**索引**:
- `stock_code`: 唯一索引

**操作方法**: `StockInfo.query_stock_intro()`, `StockInfo.save_stock_buz_intro()`

---

## TDengine 数据模型

### 股票分笔数据超级表 (SuperTable: `stock_tick`)

存储每只股票的高频分笔成交数据，使用超级表设计实现高效时序存储。

**超级表结构**:

```sql
CREATE STABLE stock_tick (
    ts TIMESTAMP,                  -- 时间戳（纳秒精度）
    trade_day NCHAR(10),          -- 交易日期
    transaction_time NCHAR(10),     -- 成交时间（HH:MM:SS）
    transaction_price FLOAT,        -- 成交价格
    price_change FLOAT,            -- 价格变动
    trading_volume BIGINT,          -- 成交量
    transaction_volume FLOAT,       -- 成交金额
    nature_type TINYINT            -- 性质类型（1=买盘，-1=卖盘，0=中性）
) TAGS (
    real_code NCHAR(10),          -- 真实股票代码（不含交易所前缀）
    exchange NCHAR(4)             -- 交易所代码（sh/sz/bj）
);
```

**子表命名规则**: `{stock_code}` (如 `sh600000`, `sz000001`)

**字段说明**:

| 字段名 | 类型 | 说明 |
|--------|------|------|
| ts | TIMESTAMP | 主键时间戳，精确到纳秒 |
| trade_day | NCHAR(10) | 交易日期 (YYYY-MM-DD) |
| transaction_time | NCHAR(10) | 成交时间 (HH:MM:SS) |
| transaction_price | FLOAT | 成交价格 |
| price_change | FLOAT | 价格变动 |
| trading_volume | BIGINT | 成交量（手） |
| transaction_volume | FLOAT | 成交金额 |
| nature_type | TINYINT | 成交性质：1=买盘，-1=卖盘，0=中性 |
| real_code (TAG) | NCHAR(10) | 股票代码标签（如 600000） |
| exchange (TAG) | NCHAR(4) | 交易所标签（sh/sz/bj） |

**插入示例** (来自 `bz_core/stock_info_api.py:305`):
```sql
INSERT INTO sh600000 USING stock_tick TAGS ("600000", "sh") VALUES (?,?,?,?,?,?,?,?)
```

**批量插入**: 每批50条记录，使用参数化插入防止SQL注入

**删除当日数据**: 删除指定日期范围的分笔数据后再插入，确保数据唯一性

**操作方法**:
- `StockInfo.query_stock_tick_store_db()`: 查询并存储分笔数据
- `StockInfo.delete_point_day_tick_data()`: 删除指定日期数据
- `StockInfo.insert_stock_tick_to_tdengine()`: 批量插入分笔数据

---

## MySQL 数据模型 (预留)

目前未设计具体表结构，预留用于事务性数据处理。

**配置** (config/application.yaml):
```yaml
mysql:
  host: '192.168.99.108'
  port: 3306
  user: 'root'
  password: 'root'
  database: 'stock_info'
```

**客户端**: `TransactionalMySQLClient` (utils/mysql_client.py)

---

## Redis 数据模型 (预留)

目前未设计具体缓存结构，预留用于热点数据缓存。

**配置** (config/application.yaml):
```yaml
redis:
  host: '192.168.99.108'
  port: 6379
  db: 0
  password: ''
```

**客户端**: `RedisClient` (utils/redis_client.py)

---

## 数据流向

```
akshare/baostock API
    ↓
StockInfo 类处理
    ↓
    ├─→ MongoDB (stock_db)
    │   ├─ all_stock_basic (实时行情)
    │   ├─ stock_daily_k_history (历史K线)
    │   └─ stock_business_intro (业务介绍)
    │
    └─→ TDengine (stock_tick_info)
        └─ stock_tick 超级表 (分笔数据)
```

---

## 字典映射文件

### 中英文字段映射 (bz_core/stock_dict.py)

| 字典名称 | 用途 |
|---------|------|
| `stock_dict_zh_2_en` | 股票基本信息中英文字段映射 |
| `stock_dict_en_2_zh` | 股票基本信息英中文字段映射 |
| `stock_tick_dict` | 分笔数据中英文字段映射 |
| `stock_tick_dict_en_2_zh` | 分笔数据英中文字段映射 |
| `stock_intro_dict` | 业务介绍中英文字段映射 |
| `stock_intro_dict_en_2_zh` | 业务介绍英中文字段映射 |

---

## 数据库客户端

### MongoDB 客户端 (utils/mongo_util.py)

**类名**: `MongoManager`

**常用方法**:
- `insert_one(collection, document)`: 插入单条文档
- `insert_many(collection, documents)`: 批量插入
- `find_one(collection, query)`: 查询单条文档
- `find(collection, query, projection, limit)`: 查询多条文档
- `get_cursor_paginated_data(collection, query, last_id, page_size)`: 游标分页查询
- `update_one(collection, query, update, upsert)`: 更新单条文档

**使用示例** (utils/db_tool_init.py):
```python
mongo_client = MongoManager(host=..., port=..., database_name="stock_db")
```

### TDengine 客户端 (utils/td_genie_client.py)

**类名**: `TDEngineClient`

**常用方法**:
- `execute(sql)`: 执行非查询语句
- `query(sql)`: 执行查询，返回字典列表
- `insert_many(sql, data)`: 批量参数化插入

**使用示例** (utils/db_tool_init.py):
```python
td_engine_client = TDEngineClient(host=..., port=..., database="stock_tick_info")
```

### MySQL 客户端 (utils/mysql_client.py)

**类名**: `TransactionalMySQLClient`

**特性**: 支持自动事务管理，默认单条 execute 即为一个原子事务

**常用方法**:
- `execute(sql, args)`: 执行 INSERT/UPDATE/DELETE
- `executemany(sql, args_list)`: 批量执行
- `query(sql, args)`: 执行 SELECT 查询
- `transaction()`: 事务上下文管理器

---

## 初始化脚本

所有数据库客户端在 `utils/db_tool_init.py` 中初始化：

```python
mysql_client = init_mysql()
mongo_client = init_mongo_db()
redis_client = init_redis()
td_engine_client = init_td_engine_client()
```

---

## 待完善项

1. **MongoDB**: 添加更多索引优化查询性能
2. **TDengine**: 考虑设置数据保留策略（RETENTION）
3. **MySQL**: 设计具体的事务性数据表结构
4. **Redis**: 设计缓存键命名规范和过期策略
