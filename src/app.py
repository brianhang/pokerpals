from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return r'<a href="venmo://paycharge?txn=charge&recipients=mattpenguin&amount=9&note=Note">Hello</a>'

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
