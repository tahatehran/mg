from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from urllib.parse import quote, urlparse
import requests
import json
import os
import socket
import ipaddress

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

ALLOWED_API_HOSTS = {'newsapi.org', 'www.newsapi.org'}


def _data_file(filename):
    """Resolve a file inside data/ and refuse anything escaping that folder."""
    data_root = os.path.realpath(DATA_DIR)
    path = os.path.realpath(os.path.join(data_root, filename))
    if os.path.commonpath([path, data_root]) != data_root:
        raise ValueError('Invalid data file path')
    return path


def _is_safe_api_url(url):
    """Allow only http/https requests to known hosts on public IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    host = (parsed.hostname or '').lower()
    if not host or host not in ALLOWED_API_HOSTS:
        return False
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    try:
        addr_infos = socket.getaddrinfo(host, port)
    except socket.gaierror:
        return False
    for info in addr_infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_reserved
                or ip.is_link_local or ip.is_multicast or ip.is_unspecified):
            return False
    return True


def load_users():
    users_path = _data_file('users.json')
    if not os.path.exists(users_path):
        with open(users_path, 'w') as file:
            json.dump({"users": []}, file)
    with open(users_path, 'r') as file:
        return json.load(file)

def save_users(users):
    with open(_data_file('users.json'), 'w') as file:
        json.dump(users, file)

def load_api_keys():
    keys_path = _data_file('api_keys.json')
    if not os.path.exists(keys_path):
        with open(keys_path, 'w') as file:
            json.dump({"newsapi_key": "", "coinmarketcap_key": ""}, file)
    with open(keys_path, 'r') as file:
        return json.load(file)

def save_api_keys(newsapi_key, coinmarketcap_key):
    api_keys = load_api_keys()
    api_keys['newsapi_key'] = newsapi_key
    api_keys['coinmarketcap_key'] = coinmarketcap_key
    with open(_data_file('api_keys.json'), 'w') as file:
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
    symbol = quote(crypto_symbol.strip(), safe='')
    url = f"https://newsapi.org/v2/everything?q={symbol}&apiKey={api_key}&language=en&sortBy=publishedAt&pageSize={articles_count}"
    if not _is_safe_api_url(url):
        return []
    response = requests.get(url, allow_redirects=False, timeout=10)
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
