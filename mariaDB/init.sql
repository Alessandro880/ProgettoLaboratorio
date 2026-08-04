CREATE DATABASE IF NOT EXISTS user_db;

CREATE USER IF NOT EXISTS 'user'@'localhost' IDENTIFIED BY 'user';
CREATE USER IF NOT EXISTS 'user'@'127.0.0.1' IDENTIFIED BY 'user';
GRANT ALL PRIVILEGES ON user_db.* TO 'user'@'localhost';
GRANT ALL PRIVILEGES ON user_db.* TO 'user'@'127.0.0.1';
FLUSH PRIVILEGES;

-- 3. Seleziona il database e crea la tabella
USE user_db;

CREATE TABLE users(
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL
);

INSERT INTO users (name, email) VALUES
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Charlie', 'charlie@example.com');