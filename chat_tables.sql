-- SQL to create chat tables manually if migrations don't work

-- Create chat_chatsession table
CREATE TABLE IF NOT EXISTS chat_chatsession (
    id TEXT PRIMARY KEY,  -- UUID as text
    user_id INTEGER NOT NULL,
    coach_id INTEGER NOT NULL,
    started_at DATETIME NOT NULL,
    ended_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES auth_user (id),
    FOREIGN KEY (coach_id) REFERENCES auth_user (id)
);

-- Create chat_chatmessage table
CREATE TABLE IF NOT EXISTS chat_chatmessage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    sender_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    read BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES chat_chatsession (id),
    FOREIGN KEY (sender_id) REFERENCES auth_user (id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_chatsession_user ON chat_chatsession (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_chatsession_coach ON chat_chatsession (coach_id);
CREATE INDEX IF NOT EXISTS idx_chat_chatmessage_session ON chat_chatmessage (session_id);
CREATE INDEX IF NOT EXISTS idx_chat_chatmessage_sender ON chat_chatmessage (sender_id);
CREATE INDEX IF NOT EXISTS idx_chat_chatmessage_timestamp ON chat_chatmessage (timestamp);