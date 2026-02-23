-- ========================================================================
-- 智能股票板块异动分析系统 - MySQL数据库表结构
-- ========================================================================

-- ========================================================================
-- 板块基础数据表
-- ========================================================================
CREATE TABLE IF NOT EXISTS `board_basic` (
    `board_name` VARCHAR(100) PRIMARY KEY COMMENT '板块名称',
    `board_type` ENUM('industry', 'concept') NOT NULL COMMENT '板块类型: industry=行业, concept=概念',
    `board_code` VARCHAR(20) DEFAULT NULL COMMENT '板块代码',
    `component_count` INT DEFAULT 0 COMMENT '成分股数量',
    `industry_classification` VARCHAR(100) DEFAULT NULL COMMENT '行业分类',
    `description` TEXT DEFAULT NULL COMMENT '板块描述',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_board_type` (`board_type`),
    INDEX `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块基础数据表';

-- ========================================================================
-- 板块实时行情表
-- ========================================================================
CREATE TABLE IF NOT EXISTS `board_quote_realtime` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `quote_time` DATETIME NOT NULL COMMENT '行情时间',
    `change_rate` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '涨跌幅(%)',
    `turnover_amount` DECIMAL(20,2) DEFAULT 0.00 COMMENT '成交额(元)',
    `volume_ratio` DECIMAL(10,2) DEFAULT 0.00 COMMENT '量比',
    `net_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '资金净流入(元)',
    `limit_up_count` INT DEFAULT 0 COMMENT '涨停家数',
    `limit_down_count` INT DEFAULT 0 COMMENT '跌停家数',
    `turnover_rate` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '换手率(%)',
    `latest_price` DECIMAL(10,2) DEFAULT 0.00 COMMENT '最新价',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_board_time` (`board_name`, `quote_time`),
    INDEX `idx_quote_time` (`quote_time`),
    INDEX `idx_change_rate` (`change_rate`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块实时行情表';

-- ========================================================================
-- 板块历史行情表
-- ========================================================================
CREATE TABLE IF NOT EXISTS `board_quote_history` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `quote_date` DATE NOT NULL COMMENT '行情日期',
    `open_price` DECIMAL(10,2) DEFAULT 0.00 COMMENT '开盘价',
    `high_price` DECIMAL(10,2) DEFAULT 0.00 COMMENT '最高价',
    `low_price` DECIMAL(10,2) DEFAULT 0.00 COMMENT '最低价',
    `close_price` DECIMAL(10,2) DEFAULT 0.00 COMMENT '收盘价',
    `change_rate` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '涨跌幅(%)',
    `turnover_amount` DECIMAL(20,2) DEFAULT 0.00 COMMENT '成交额(元)',
    `net_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '资金净流入(元)',
    `volume` DECIMAL(20,2) DEFAULT 0.00 COMMENT '成交量',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY `uk_board_date` (`board_name`, `quote_date`),
    INDEX `idx_quote_date` (`quote_date`),
    INDEX `idx_board_name` (`board_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块历史行情表';

-- ========================================================================
-- 异动板块记录表
-- ========================================================================
CREATE TABLE IF NOT EXISTS `board_anomaly` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `anomaly_time` DATETIME NOT NULL COMMENT '异动触发时间',
    `change_rate` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '触发时涨跌幅(%)',
    `turnover_amount` DECIMAL(20,2) DEFAULT 0.00 COMMENT '触发时成交额(元)',
    `volume_ratio` DECIMAL(10,2) DEFAULT 0.00 COMMENT '触发时量比',
    `net_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '触发时资金净流入(元)',
    `limit_up_count` INT DEFAULT 0 COMMENT '触发时涨停家数',
    `strength_score` DECIMAL(4,2) DEFAULT 0.00 COMMENT '强度评分(0-1)',
    `is_new_anomaly` BOOLEAN DEFAULT FALSE COMMENT '是否为新异动(相对于上次异动)',
    `is_processed` BOOLEAN DEFAULT FALSE COMMENT '是否已处理归因',
    `processed_time` DATETIME DEFAULT NULL COMMENT '处理时间',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_anomaly_time` (`anomaly_time`),
    INDEX `idx_board_name` (`board_name`),
    INDEX `idx_is_processed` (`is_processed`),
    INDEX `idx_strength_score` (`strength_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异动板块记录表';

-- ========================================================================
-- 板块成分股表
-- ========================================================================
CREATE TABLE IF NOT EXISTS `board_component` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `stock_code` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `stock_name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `weight` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '权重(%)',
    `add_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '添加时间',
    UNIQUE KEY `uk_board_stock` (`board_name`, `stock_code`),
    INDEX `idx_stock_code` (`stock_code`),
    INDEX `idx_weight` (`weight`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块成分股表';

-- ========================================================================
-- 板块资金流向表
-- ========================================================================
CREATE TABLE IF NOT EXISTS `board_fund_flow` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增ID',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `flow_date` DATE NOT NULL COMMENT '资金流日期',
    `main_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '主力净流入(元)',
    `super_large_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '超大单净流入(元)',
    `large_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '大单净流入(元)',
    `medium_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '中单净流入(元)',
    `small_inflow` DECIMAL(20,2) DEFAULT 0.00 COMMENT '小单净流入(元)',
    `main_inflow_ratio` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '主力净流入占比(%)',
    `super_large_inflow_ratio` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '超大单净流入占比(%)',
    `large_inflow_ratio` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '大单净流入占比(%)',
    `medium_inflow_ratio` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '中单净流入占比(%)',
    `small_inflow_ratio` DECIMAL(10,4) DEFAULT 0.0000 COMMENT '小单净流入占比(%)',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY `uk_board_date` (`board_name`, `flow_date`),
    INDEX `idx_flow_date` (`flow_date`),
    INDEX `idx_main_inflow` (`main_inflow`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='板块资金流向表';

-- ========================================================================
-- 数据初始化
-- ========================================================================
-- 创建定时任务清理历史数据（保留最近90天的实时行情，保留2年的历史行情）
-- 建议通过定时任务或存储过程执行
-- DELETE FROM board_quote_realtime WHERE quote_time < DATE_SUB(NOW(), INTERVAL 90 DAY);
