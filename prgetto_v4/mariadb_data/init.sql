CREATE DATABASE IF NOT EXISTS project_db;

USE project_db;

CREATE TABLE IF NOT EXISTS web_resources(
    url VARCHAR(2048) PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    title VARCHAR(2048) NOT NULL,
    html_text LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_standard(
    url VARCHAR(2048) PRIMARY KEY,
    gold_text LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (url) REFERENCES web_resources(url) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluations (
    url VARCHAR(255) PRIMARY KEY,
    precision_val FLOAT,
    recall_val FLOAT,
    f1_val FLOAT,
    judge_score FLOAT,
    FOREIGN KEY (url) REFERENCES gold_standard(url) ON DELETE CASCADE
);

