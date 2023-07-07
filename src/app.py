from flask import Flask

from player.route import handle_home, handle_login, handle_logout

app = Flask(__name__)

@app.route("/")
def home():
    return handle_home()

@app.route("/invalid_venmo", strict_slashes=False)
def invalid_venmo():
    return "You gave an invalid username :("

@app.post('/login')
def login():
    return handle_login()

@app.post('/logout')
def logout():
    return handle_logout()

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
