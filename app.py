import json
import time

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired
from wtforms import StringField, SubmitField
from flask import Flask, render_template, request, jsonify
from celery import Celery
import eventlet
import http.client
from celery.schedules import timedelta
import asyncio
from threading import Timer, Thread
import requests
import schedule
from flask_apscheduler import APScheduler
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
app.config['CELERY_TIMEZONE'] = 'UTC'  # Добавляем настройку временной зоны
app.config['CELERYBEAT_SCHEDULE'] = {
    'update-currency-rates': {
        'task': 'tasks.update_bitcoin_rate',
        'schedule': timedelta(seconds=10),
    },
}
celery = Celery(__name__, broker=app.config['CELERY_BROKER_URL'])

socketio = SocketIO(app)
celery.conf.update(app.config)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
news = []
socketio.init_app(app)  # Добавил инициализацию SocketIO

eventlet.monkey_patch()


class Currency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), nullable=False)
    rate = db.Column(db.Float, nullable=False)


class AddItemForm(FlaskForm):
    content = StringField('Content', validators=[DataRequired()])
    submit = SubmitField('Add Item')


class DeleteItemForm(FlaskForm):
    item_id = StringField('Item ID to Delete', validators=[DataRequired()])
    submit = SubmitField('Delete Item')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    items = db.relationship('Item', backref='author', lazy=True)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))


@app.route('/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    items = Item.query.all()

    add_form = AddItemForm()
    delete_form = DeleteItemForm()

    async_task_result = None

    if add_form.validate_on_submit():
        new_item = Item(content=add_form.content.data, author=current_user)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('home'))

    if delete_form.validate_on_submit():
        item_id_to_delete = delete_form.item_id.data
        item_to_delete = Item.query.get(item_id_to_delete)
        if item_to_delete:
            db.session.delete(item_to_delete)
            db.session.commit()
            flash('Item deleted successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Item not found!', 'danger')

    return render_template('home.html', items=items, add_form=add_form, delete_form=delete_form, )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/account')
@login_required
def account():
    return render_template('account.html')


@app.route('/delete_item/<int:item_id_to_delete>', methods=['GET', 'POST'])
@login_required
def delete_item(item_id_to_delete):
    item_to_delete = Item.query.get(item_id_to_delete)
    if item_to_delete:
        db.session.delete(item_to_delete)
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    else:
        flash('Item not found!', 'danger')
    return redirect(url_for('home'))


@socketio.on('connect')
def handle_connect():
    print('Client connected')


async def fib(n):
    if n > 1:
        task1 = asyncio.create_task(fib(n - 1))
        task2 = asyncio.create_task(fib(n - 2))
        await asyncio.gather(task1, task2)
        return task1.result() + task2.result()
    return n


@socketio.on('calculate_fibonacci')
def handle_calculate_fibonacci(data):
    result = asyncio.run(fib(data['n']))
    socketio.emit('fibonacci_result', {'result': result})


@app.route('/currencies', methods=['GET'])
def get_currencies():
    currencies = Currency.query.all()
    currency_list = [{'name': currency.name, 'rate': currency.rate} for currency in currencies]
    return jsonify(currency_list)


def update_bitcoin_rate():
    print('Fetching Bitcoin rate...')
    api_url = 'https://api.coindesk.com/v1/bpi/currentprice.json'
    conn = http.client.HTTPSConnection("api.coindesk.com")
    conn.request("GET", "/v1/bpi/currentprice.json")
    response = conn.getresponse()
    data = response.read().decode('utf-8')  # Decode bytes to a string
    json_data = json.loads(data)
    bitcoin_rate = json_data['bpi']['USD']['rate']
    socketio.emit('rateBitcoin', {'result': bitcoin_rate})


def run_background_task():
    while True:
        update_bitcoin_rate()
        time.sleep(60)


@socketio.on('api_weather_code')
def api_weather_code():
    global news
    print('Fetching weather data...')
    headers = {'User-Agent': 'YourAppName/1.0'}  # Replace 'YourAppName' with your actual application name
    conn = http.client.HTTPSConnection("newsapi.org")
    conn.request("GET", "/v2/top-headlines?country=ru&apiKey=00475fa15fd2446fa936d14b2da6a9e0", headers=headers)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    json_data = json.loads(data)
    news_data = json_data['articles']
    for i in range(0, len(news_data)):
        news_title = news_data[i]['title']
        news.append(news_title)
    socketio.emit('apiNewsTitles', {'result': news})
    print(news)


background_thread = Thread(target=run_background_task)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        background_thread.start()
    csrf.init_app(app)
    socketio.run(app, debug=True, use_reloader=False)
