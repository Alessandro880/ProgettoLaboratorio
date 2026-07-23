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

CREATE TABLE IF NOT EXISTS evaluation_cache (
    url VARCHAR(2048) PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    precision_score FLOAT,
    recall_score FLOAT,
    f1_score FLOAT,
    judge_score FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (url) REFERENCES web_resources(url) ON DELETE CASCADE
);

