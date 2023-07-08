import db.connection


def main():
    schema_path = 'schema.sql'

    with open(schema_path, 'r') as schema_file:
        with db.connection.open_connection() as connection:
            cursor = connection.cursor()
            cursor.executescript(schema_file.read())
            connection.commit()

    print(f"Executed {schema_path}")


if __name__ == '__main__':
    main()
