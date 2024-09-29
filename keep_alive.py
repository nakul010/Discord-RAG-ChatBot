from flask import Flask, request, Response
from flask_httpauth import HTTPBasicAuth
from threading import Thread
import logging
import os

app = Flask(__name__)

# Set up logging
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


auth = HTTPBasicAuth()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

# Sample log data (for demonstration)
log_data = []


@app.route("/")
def home():
    return "Bot is alive 😊"


@app.route("/logs")
@auth.login_required
def view_logs():
    with open("bot.log", "r") as log_file:
        logs = log_file.read()
    return f"<pre>{logs}</pre>"


@auth.verify_password
def verify_password(username, password):
    return username == USERNAME and password == PASSWORD


def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


def keep_alive():
    t = Thread(target=run)
    t.start()
