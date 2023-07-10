DOLLAR_TO_CENTS = 100.0


def to_string(cents: int) -> str:
    return '{:.2f}'.format(cents / DOLLAR_TO_CENTS)
