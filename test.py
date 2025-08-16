from flask import Flask, render_template
import json

# Max 45 button


HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")









@app.route("/api/getAircraftName")
def getAicraftName():

    with open("data.json", "r", encoding="utf-8") as f:
        data = json.load(f) 

    print(data)
    
    aicraftName = list(data.keys())
    
    return aicraftName


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
