#!/bin/bash

# Activate virtual environment
source /tmp/8dd9c5067c8a931/antenv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install additional required packages
pip install flask-socketio==5.3.6 eventlet==0.35.2

# Run database migrations
flask db upgrade

# Start Gunicorn with eventlet worker
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8000 app:app 