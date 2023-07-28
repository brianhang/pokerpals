from functools import lru_cache
import io
from typing import Optional
from flask import Response, request, send_file, url_for
import qrcode


@lru_cache(maxsize=16)
def generate_qr_code_image(game_id: int, entry_code: Optional[str]):
    join_url = url_for('game_join_form', game_id=game_id,
                       code=entry_code, _external=True)
    qr_code = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=1,
    )
    qr_code.add_data(join_url)
    qr_code.make(fit=True)

    return qr_code.make_image(fill_color="black", back_color="white")


def handle_game_join_qr_code(game_id: int, entry_code: Optional[str]) -> Response:
    image = generate_qr_code_image(game_id, entry_code)
    image_buf = io.BytesIO()
    image.save(image_buf)
    image_buf.seek(0)
    return send_file(image_buf, mimetype="image/png")
