import src.db.cursor as clib
import src.db.queries

def setup(cur):
    query = r'INSERT INTO games(lobby_name, buyin_cents) '\
    r'VALUES ("test_lobby", 10000);'
    print(query)

    cur.execute(query)



if __name__ == '__main__':
    print(clib.get)
    with clib.get() as c:
        setup(c)

