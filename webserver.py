from flask import flask
from threading import Thread

at = Flask('')
@app.route('/')
def home():
    return "discord bot.ok"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
