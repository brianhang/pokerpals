DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS game_players;
DROP TABLE IF EXISTS game_payments;

CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lobby_name TEXT NOT NULL,
    buyin_cents INTEGER NOT NULL,
    entry_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    payout_type INTEGER
);

CREATE TABLE players (
    venmo_username TEXT PRIMARY KEY NOT NULL,
    active_game_id INTEGER
);

CREATE TABLE game_players (
    game_id INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    join_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    buyin_cents INTEGER NOT NULL,
    cashout_cents INTEGER,
    PRIMARY KEY (game_id, player_id)
);

CREATE TABLE game_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    from_player_id TEXT NOT NULL,
    to_player_id TEXT NOT NULL,
    cents INTEGER NOT NULL,
    completed BOOLEAN NOT NULL
);
