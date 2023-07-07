import src.db.cursor as clib
import src.db.queries as queries

def setup(cur):
    query = r'INSERT INTO games(id, lobby_name, buyin_amt_cents) '\
    r'VALUES (1, "test_lobby", 10000);'
    print(query)
    cur.execute(query)

    query = r'INSERT INTO players(venmo_username, game_id, total_buyin_chips, final_chips) '\
    r'VALUES ("user1", 1, 200, 300), ("user2", 1, 200, 100);'
    print(query)
    cur.execute(query)



if __name__ == '__main__':
    print(clib.get)
    with clib.get() as cur:
#          setup(cur)
        query = queries.get_payout_query(1)
        print(query)
        cur.execute(query)
        print(cur.fetchall())

