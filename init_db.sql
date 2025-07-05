CREATE TABLE IF NOT EXISTS prompts (
    user TEXT,
    task_type TEXT,
    prompt TEXT,
    version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS responses (
    user TEXT,
    task_type TEXT,
    response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
