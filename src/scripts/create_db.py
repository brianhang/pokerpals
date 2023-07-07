from os import getcwd

import db.cursor

def main():
    schema_path = 'schema.sql'

    with open(schema_path, 'r') as schema_file:
        with db.cursor.get() as cursor:
            cursor.executescript(schema_file.read())
    print(f"Executed {schema_path}")

if __name__ == '__main__':
    main()
