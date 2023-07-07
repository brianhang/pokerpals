from flask import Flask, request
from html import escape as html_escape

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
    <title>Venmo Login</title>
    </head>
    <body>
    <form action="/login" method="post">
        <label for="venmo-username">Venmo Username:</label>
        <input type="text" id="venmo-username" name="venmo-username" required>
        <br>
        <input type="submit" value="Submit">
    </form>
    </body>
    </html>
    """

@app.post('/login')
def login():
    venmo_username = request.form.get('venmo-username')
    return f'TODO: Create or get player with venmo username = {html_escape(venmo_username)}'

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8080)
