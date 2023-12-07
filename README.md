# Flask-SocketIO-App

**Version:** 1.0.0

## Description

Flask-SocketIO-App is a web application built using the Flask framework and Flask-SocketIO library. It provides a simple interface for managing a to-do list and implements functionality to fetch Bitcoin rates and news headlines through external APIs.

## Features

1. **Task Management:**
    - Add a new task.
    - View the list of tasks.
    - Delete a task.

2. **Calculate Fibonacci Numbers:**
    - Compute Fibonacci numbers for a given value.

3. **Bitcoin Rate Tracker:**
    - Automatically update the Bitcoin rate using a background thread.

4. **API Weather:**
    - Fetch news headlines from an external source via API.

## Technologies

- Python 3.9
- Flask 2.0.1
- Flask-SocketIO 5.1.1
- SQLAlchemy 2.0.0
- APScheduler 3.7.0
- Requests 2.26.0

## Installation Instructions

1. Install Python 3.9 or higher.
2. Create and activate a virtual environment.
3. Install dependencies from the `requirements.txt` file using `pip install -r requirements.txt`.
4. Run the application with `python app.py`.
5. Access the application in your browser at `http://localhost:5000`.

## Configuration

- Adjust application parameters in the `config.py` file, such as API keys and database settings.

## Unit Testing

To ensure code quality, the application includes a set of unit tests. Run the tests using:

```bash
python -m unittest discover tests