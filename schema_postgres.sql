DROP TABLE IF EXISTS user_service_tags;
DROP TABLE IF EXISTS service_tags;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    location TEXT,
    telegram TEXT,
    website TEXT,
    bio TEXT,
    skills TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE service_tags (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT
);

CREATE TABLE user_service_tags (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES service_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, tag_id)
);
