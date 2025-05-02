# CareNest - Healthcare Management Platform

CareNest is a comprehensive healthcare management platform that enables doctors, nurses, and patients to collaborate effectively in managing healthcare plans and tracking patient progress.

## Features

- User authentication with email/password and Google OAuth
- Role-based access control (Doctor, Nurse, Patient)
- Patient management
- Care plan creation and tracking
- Goal setting and monitoring
- Activity tracking
- Real-time messaging
- Notifications system
- Analytics dashboard
- Profile and settings management

## Tech Stack

- Backend: Python Flask
- Database: SQLite
- Frontend: HTML, CSS (Bootstrap 5), JavaScript
- Authentication: Flask-Login, Google OAuth
- ORM: SQLAlchemy

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/carenest.git
cd carenest
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following content:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Running the Application

1. Start the Flask development server:
```bash
flask run
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## Development

- The application follows a modular structure:
  - `app/` - Main application directory
  - `app/templates/` - Jinja2 templates
  - `app/static/` - Static files (CSS, JS, images)
  - `app/models/` - Database models
  - `app.py` - Application entry point

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 