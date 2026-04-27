CREATE TABLE IF NOT EXISTS urls (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    long_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS visits (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    visited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_urls_code ON urls(code);
CREATE INDEX IF NOT EXISTS idx_visits_code ON visits(code);

\echo 'Database initialized successfully!'