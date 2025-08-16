from flask import Flask, render_template


HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
