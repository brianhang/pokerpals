import db


COLUMN_NAME = 'payout_type'


def migrate_add_payout_type():
    with db.connection.open_connection() as connection:
        cursor = connection.cursor()
        cursor.execute('PRAGMA table_info(games);')
        columns = [info[1] for info in cursor.fetchall()]

        if COLUMN_NAME not in columns:
            cursor.execute(
                f'ALTER TABLE games ADD COLUMN {COLUMN_NAME} INTEGER;',
            )
            print(f'Added {COLUMN_NAME} column to games')

        connection.commit()
