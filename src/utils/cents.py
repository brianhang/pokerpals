from typing import Optional

def to_string(tot_cents: int) -> str:
    dollars = tot_cents // 100
    cents = tot_cents % 100
    return '{:0>1}.{:0>2}'.format(dollars, cents)

def from_string(s :str) -> Optional[int]:
    try:
        dollars, _, cents = s.partition('.')
        dollars = int(dollars or 0)
        cents = int(cents or 0)

        if dollars < 0: return None
        if cents < 0 or cents >= 100: return None

        return dollars * 100 + cents
    except ValueError:
        return None
