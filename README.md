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

Without the Twilio variables (and without `APP_DEBUG`), nobody can log in.

### Migrating from Venmo logins

PokerPal used to log people in with just their Venmo username. On start, the
app migrates the database so that every Venmo username becomes a user with that
Venmo username attached, and backs up the database first to
`database.db.pre-users-<timestamp>.bak`. The old `players` table is kept as
`legacy_players`.

After logging in with a phone number for the first time, people can claim their
old Venmo profile to keep their game history and payments. Each Venmo profile
can only be claimed by one phone number.
