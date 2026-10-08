"""
Gunicorn reads this file automatically when started from the src/ directory.

Settings passed on the command line still apply; this only adds hooks.
"""


def on_starting(server):
    """
    Runs once in the master process, before any workers start, so the
    database is migrated before the app serves any requests. If a migration
    fails, gunicorn exits instead of starting.
    """
    from migrations.run import run_migrations
    from utils.secret_key import load_secret_key

    run_migrations()

    # Create the session signing key now, so every worker reads the same one
    load_secret_key()
