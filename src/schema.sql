DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_payment_methods;
DROP TABLE IF EXISTS game_players;
DROP TABLE IF EXISTS game_payments;

CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lobby_name TEXT NOT NULL,
    buyin_cents INTEGER NOT NULL,
    entry_code TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    payout_type INTEGER
);

-- A person using PokerPal. `phone_number` (E.164) is how they log in. Users
-- migrated from the old Venmo-username login have no phone number until they
-- log in with a phone and claim their old Venmo profile.
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number TEXT UNIQUE,
    display_name TEXT NOT NULL,
    active_game_id INTEGER,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Ways to pay a user, e.g. method 'venmo' with their Venmo username as handle.
CREATE TABLE user_payment_methods (
    user_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    handle TEXT NOT NULL,
    PRIMARY KEY (user_id, method),
    UNIQUE (method, handle)
);

CREATE TABLE game_players (
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    join_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    buyin_cents INTEGER NOT NULL,
    cashout_cents INTEGER,
    PRIMARY KEY (game_id, player_id)
);

CREATE TABLE game_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    from_player_id INTEGER NOT NULL,
    to_player_id INTEGER NOT NULL,
    cents INTEGER NOT NULL,
    completed BOOLEAN NOT NULL
);
