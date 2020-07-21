from flask import Flask
app = Flask(__name__)


@app.route('/')
def hello_world():
    print('Connected')
    return 'Connected'


app.run(port=8080)