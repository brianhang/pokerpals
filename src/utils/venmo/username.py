import urllib.parse
from functools import lru_cache

import requests


@lru_cache(256)
def is_valid_venmo_username(venmo_username: str) -> bool:
    try:
        # lol
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'}
        url = f'https://account.venmo.com/u/{urllib.parse.quote(venmo_username)}'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        # TODO: should probably not cache false if we got a transient error
        pass

    return False
