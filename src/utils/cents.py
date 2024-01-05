from typing import Optional


def to_numerical_string(tot_cents: int) -> str:
    """
    Returns the human-readable string for an integer representing the number of
    cents in the format "XX.XX"
    Negative values are allowed and will be displayed as "-XX.XX"
    """
    dollars = abs(tot_cents) // 100
    cents = abs(tot_cents) % 100
    s = '{:0>1}.{:0>2}'.format(dollars, cents)

    return '-'+s if tot_cents < 0 else s


def to_string(tot_cents: int) -> str:
    """
    Returns the human-readable string for an integer representing the number of
    cents in the format "$XX.XX"
    Negative values are allowed and will be displayed as "-$XX.XX"
    """
    s = to_numerical_string(tot_cents)
    if s[0] == '-':
        return '-$'+s[1:]
    return '$'+s

def from_string(s :str) -> Optional[int]:
    """
    Converts the input string in the format "XXX.XX" to an integer representing
    number of cents.  None is returned if the string can not be parsed.
    """
    try:
        dollars, _, cents = s.partition('.')
        while len(cents) < 2:
            cents += '0'
        dollars = int(dollars or 0)
        cents = int(cents or 0)

        if cents < 0 or cents >= 100: return None

        amt = abs(dollars) * 100 + cents
        if dollars < 0:
            amt *= -1
        return amt
    except ValueError:
        return None
