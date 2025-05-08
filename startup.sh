#!/bin/bash

# Create instance directory if it doesn't exist
mkdir -p /home/site/wwwroot/instance

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=production

# Run database migrations
cd /home/site/wwwroot
flask db upgrade

# Start the application
gunicorn --bind=0.0.0.0 --timeout 600 app:app 