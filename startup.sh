#!/bin/bash

# Activate virtual environment
source /tmp/8dd9c5067c8a931/antenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start Gunicorn
gunicorn --config gunicorn.conf.py app:app 