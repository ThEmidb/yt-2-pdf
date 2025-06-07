from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "This app cannot run properly on Vercel. Use Heroku instead."

# Export Flask app for Vercel
handler = app