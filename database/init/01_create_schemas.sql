CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS clean;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- =====================
-- RAW DATA
-- =====================
CREATE TABLE IF NOT EXISTS raw.real_estate_raw (
    id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100),
    batch_number INTEGER,
    group_number INTEGER,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    row_index INTEGER,
    raw_data JSONB,
    status VARCHAR(20) DEFAULT 'loaded'
);

CREATE TABLE IF NOT EXISTS raw.batch_metadata (
    id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100) UNIQUE,
    batch_number INTEGER,
    group_number INTEGER,
    num_records INTEGER,
    num_columns INTEGER,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_status VARCHAR(50),
    training_decision VARCHAR(50),
    training_reason TEXT,
    training_executed BOOLEAN DEFAULT FALSE,
    model_promoted BOOLEAN DEFAULT FALSE,
    promotion_reason TEXT,
    run_id VARCHAR(255),
    model_version VARCHAR(50),
    mae_candidate FLOAT,
    rmse_candidate FLOAT,
    r2_candidate FLOAT,
    mae_champion FLOAT,
    rmse_champion FLOAT,
    r2_champion FLOAT
);

-- =====================
-- INFERENCE LOGS
-- =====================
CREATE TABLE IF NOT EXISTS raw.inference_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_data JSONB,
    prediction FLOAT,
    model_name VARCHAR(255),
    model_alias VARCHAR(100),
    model_version VARCHAR(50),
    response_time_ms FLOAT,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT
);

-- =====================
-- CLEAN DATA
-- =====================
CREATE TABLE IF NOT EXISTS clean.real_estate_clean (
    id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100),
    batch_number INTEGER,
    processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    price FLOAT,
    brokered_by INTEGER,
    bed INTEGER,
    bath INTEGER,
    acre_lot FLOAT,
    house_size FLOAT,
    zip_code INTEGER,
    col_07 INTEGER,
    col_08 INTEGER,
    col_09 FLOAT,

    col_10 INTEGER, col_11 INTEGER, col_12 INTEGER,
    col_13 INTEGER, col_14 INTEGER, col_15 INTEGER,
    col_16 INTEGER, col_17 INTEGER, col_18 INTEGER,
    col_19 INTEGER, col_20 INTEGER, col_21 INTEGER,
    col_22 INTEGER, col_23 INTEGER, col_24 INTEGER,
    col_25 INTEGER, col_26 INTEGER, col_27 INTEGER,
    col_28 INTEGER, col_29 INTEGER, col_30 INTEGER,
    col_31 INTEGER, col_32 INTEGER, col_33 INTEGER,
    col_34 INTEGER, col_35 INTEGER, col_36 INTEGER,
    col_37 INTEGER, col_38 INTEGER, col_39 INTEGER,
    col_40 INTEGER, col_41 INTEGER, col_42 INTEGER,
    col_43 INTEGER, col_44 INTEGER, col_45 INTEGER,
    col_46 INTEGER, col_47 INTEGER, col_48 INTEGER,
    col_49 INTEGER, col_50 INTEGER, col_51 INTEGER,
    col_52 INTEGER, col_53 INTEGER, col_54 INTEGER,

    is_valid BOOLEAN DEFAULT TRUE,
    anomaly_flags JSONB
);

-- =====================
-- MONITORING
-- =====================
CREATE TABLE IF NOT EXISTS monitoring.model_training_runs (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(255),
    model_name VARCHAR(255),
    model_version VARCHAR(50),
    batch_id VARCHAR(100),
    train_size INTEGER,
    val_size INTEGER,
    test_size INTEGER,
    mae FLOAT,
    rmse FLOAT,
    mape FLOAT,
    r2 FLOAT,
    mae_champion FLOAT,
    rmse_champion FLOAT,
    promoted_to_champion BOOLEAN DEFAULT FALSE,
    promotion_reason TEXT,
    training_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitoring.data_drift (
    id BIGSERIAL PRIMARY KEY,
    batch_id VARCHAR(100),
    column_name VARCHAR(100),
    mean_historical FLOAT,
    mean_current FLOAT,
    std_historical FLOAT,
    std_current FLOAT,
    drift_score FLOAT,
    drift_detected BOOLEAN DEFAULT FALSE,
    detection_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);