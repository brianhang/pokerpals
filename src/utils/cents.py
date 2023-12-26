
def to_string(tot_cents: int) -> str:
    dollars = tot_cents // 100
    cents = tot_cents % 100
    return '{}.{:0>2}'.format(dollars, cents)
