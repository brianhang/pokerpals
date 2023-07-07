DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;

CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lobby_name TEXT NOT NULL,
    buyin_cents INTEGER NOT NULL
);

CREATE TABLE players (
    venmo_username TEXT PRIMARY KEY NOT NULL,
    game_id INTEGER,
    total_chips INTEGER, 
    final_chips INTEGER
)
