CREATE DATABASE IF NOT EXISTS project_db;
USE project_db;

CREATE TABLE IF NOT EXISTS web_resources (
    url VARCHAR(2048) CHARACTER SET ascii PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    title VARCHAR(2048) NOT NULL,
    html_text LONGTEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_standard (
    url VARCHAR(2048) CHARACTER SET ascii PRIMARY KEY,
    gold_text LONGTEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_gold_web FOREIGN KEY (url) REFERENCES web_resources(url) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluations (
    url VARCHAR(2048) CHARACTER SET ascii PRIMARY KEY,
    precision_val FLOAT,
    recall_val FLOAT,
    f1_val FLOAT,
    seq_ratio FLOAT,
    seq_match FLOAT,
    seq_perfect BOOLEAN,
    judge_score INT,
    CONSTRAINT fk_eval_gold FOREIGN KEY (url) REFERENCES gold_standard(url) ON DELETE CASCADE
);