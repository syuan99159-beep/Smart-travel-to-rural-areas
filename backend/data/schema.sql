PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS spots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    area TEXT NOT NULL,
    category TEXT NOT NULL,
    trip_length TEXT NOT NULL,
    stay_type TEXT NOT NULL,
    stay_minutes INTEGER NOT NULL,
    budget TEXT NOT NULL,
    indoor_outdoor TEXT NOT NULL,
    can_dine INTEGER NOT NULL DEFAULT 0,
    meal_type TEXT NOT NULL DEFAULT '無',
    description TEXT DEFAULT '',
    image TEXT DEFAULT '',
    keywords TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spots_area ON spots(area);
CREATE INDEX IF NOT EXISTS idx_spots_category ON spots(category);
CREATE INDEX IF NOT EXISTS idx_spots_trip_length ON spots(trip_length);
CREATE INDEX IF NOT EXISTS idx_spots_stay_type ON spots(stay_type);

CREATE TABLE IF NOT EXISTS itineraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_json TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    itinerary_length TEXT NOT NULL,
    origin_label TEXT NOT NULL DEFAULT '起點',
    total_stay_minutes INTEGER NOT NULL DEFAULT 0,
    total_travel_minutes INTEGER NOT NULL DEFAULT 0,
    is_rushed INTEGER NOT NULL DEFAULT 0,
    rush_reason TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS itinerary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL,
    item_order INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    spot_id INTEGER,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    stay_minutes INTEGER NOT NULL DEFAULT 0,
    travel_minutes INTEGER NOT NULL DEFAULT 0,
    meal_type TEXT NOT NULL DEFAULT '無',
    notes TEXT DEFAULT '',
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE,
    FOREIGN KEY (spot_id) REFERENCES spots(id)
);

CREATE INDEX IF NOT EXISTS idx_itinerary_items_itinerary_id ON itinerary_items(itinerary_id);

CREATE TABLE IF NOT EXISTS travel_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_key TEXT NOT NULL,
    destination_key TEXT NOT NULL,
    travel_minutes INTEGER NOT NULL,
    distance_text TEXT,
    duration_text TEXT,
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(origin_key, destination_key)
);

CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    parsed_json TEXT DEFAULT '{}',
    result_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS latest_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    published_at TEXT NOT NULL,
    summary TEXT DEFAULT '',
    source TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_latest_news_published_at ON latest_news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_latest_news_sort_order ON latest_news(sort_order ASC);
