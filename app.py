from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USERS_FILE = 'data/users.json'
API_KEYS_FILE = 'data/api_keys.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as file:
            json.dump({"users": []}, file)
    with open(USERS_FILE, 'r') as file:
        return json.load(file)

def save_users(users):
    with open(USERS_FILE, 'w') as file:
        json.dump(users, file)

def load_api_keys():
    if not os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, 'w') as file:
            json.dump({"newsapi_key": "", "coinmarketcap_key": ""}, file)
    with open(API_KEYS_FILE, 'r') as file:
        return json.load(file)

def save_api_keys(newsapi_key, coinmarketcap_key):
    api_keys = load_api_keys()
    api_keys['newsapi_key'] = newsapi_key
    api_keys['coinmarketcap_key'] = coinmarketcap_key
    with open(API_KEYS_FILE, 'w') as file:
        json.dump(api_keys, file)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        for user in users['users']:
            if user['username'] == username and user['password'] == password:
                session['username'] = username
                return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        for user in users['users']:
            if user['username'] == username:
                return "Username already exists"
        users['users'].append({"username": username, "password": password})
        save_users(users)
        return redirect(url_for('login'))
        return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api_keys', methods=['GET', 'POST'])
def api_keys():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        newsapi_key = request.form['newsapi_key']
        coinmarketcap_key = request.form['coinmarketcap_key']
        save_api_keys(newsapi_key, coinmarketcap_key)
        return redirect(url_for('dashboard'))
    return render_template('api_keys.html')

@app.route('/crypto_news/<crypto_symbol>')
def crypto_news(crypto_symbol):
    api_keys = load_api_keys()
    newsapi_key = api_keys.get('newsapi_key')
    articles = get_crypto_news(newsapi_key, crypto_symbol)
    return jsonify(articles)

def get_crypto_news(api_key, crypto_symbol, articles_count=10):
    url = f"https://newsapi.org/v2/everything?q={crypto_symbol}&apiKey={api_key}&language=en&sortBy=publishedAt&pageSize={articles_count}"
    response = requests.get(url)
    if response.status_code == 200:
        news_data = response.json()
        articles = news_data.get('articles', [])
        crypto_news = []
        for article in articles:
            title = article.get('title', 'No Title')
            description = article.get('description', 'No Description')
            url = article.get('url', '#')
            published_at = article.get('publishedAt', 'No Date')
            crypto_news.append({
                "title": title,
                "description": description,
                "url": url,
                "publishedAt": published_at
            })
        return crypto_news
    else:
        return []

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)