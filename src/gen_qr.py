import qrcode
import io


# Returns the bytes for the png corresponding to the input link
def get_png_bytes(link):
    img = qrcode.make(link)
    byte_stream = io.BytesIO()
    img.save(byte_stream)
    return byte_stream

if __name__ == '__main__':
    link = 'venmo://paycharge?txn=charge&recipients=mattpenguin&amount=10&note=Note'
    
    with open('test.png', 'wb') as f:
        bytes = get_png_bytes(link)
        f.write(bytes.getvalue())


