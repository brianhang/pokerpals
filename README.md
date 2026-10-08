# PokerPal

## Development
First, make sure you are in an environment that has Bash and Python 3. Then, run:
```
./dev.sh
```

### Testing

To run all unit tests, run `python3 -m unittest discover tests` from the src/ directory.

To run a specifc unit test, run `python3 -m unittest tests.test_utils_cents` from the src/ directory.

## Logging In

People log in with their phone number and a code texted to them. In
development (`./dev.sh`), codes are printed to the server log instead of being
texted.

In production, codes are sent with [Twilio Verify](https://www.twilio.com/docs/verify).
Set these environment variables for the app:

| Variable | Value |
| --- | --- |
| `TWILIO_ACCOUNT_SID` | Twilio account SID (`AC...`) |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_VERIFY_SERVICE_SID` | Verify service SID (`VA...`) |
| `APP_SECRET_KEY` | Optional. Signs login cookies. If unset, a random key is generated and saved to a `secret_key` file next to the database. |

Without the Twilio variables (and without `APP_DEBUG`), phone verification is
off: people log in by entering a phone number, with no code, and the app logs a
warning on start. Set the variables at any time to turn verification on.

## Database Migrations

Migrations run automatically before the app starts serving:

- With gunicorn started from `src/`, the `on_starting` hook in
  `src/gunicorn.conf.py` runs them once, before any workers start. If one
  fails, gunicorn exits instead of starting.
- With `python app.py` (as `./dev.sh` does), they run before the server starts.
- By hand: `python -m scripts.migrate` from `src/`.

If the app is started on a database with pending migrations, it refuses to
start and logs which migrations are pending.

### Migrating from Venmo logins

PokerPal used to log people in with just their Venmo username. On start, the
app migrates the database so that every Venmo username becomes a user with that
Venmo username attached, and backs up the database first to
`database.db.pre-users-<timestamp>.bak`. The old `players` table is kept as
`legacy_players`.

After logging in with a phone number for the first time, people can claim their
old Venmo profile to keep their game history and payments. Each Venmo profile
can only be claimed by one phone number.

## Profiles and Payments

Each person has a profile (`/u/<id>`) with the ways they can be paid, and can
edit their name, Venmo username and Zelle phone number or email at `/account`.
Zelle details are only shown to people who have played in a game with them.

Each payment has a page (`/payment/<id>`) with every way to settle it: a Venmo
link that opens the app with the amount filled in, and, since Zelle has no
equivalent link, the recipient's Zelle phone number or email and the amount
with copy buttons, to paste into a bank app.
