from collections import namedtuple

Transaction = namedtuple("Transaction", ["sender_id", "receiver_id", "cents"])
