from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from oauthlib.oauth2 import WebApplicationClient
import os
from dotenv import load_dotenv
from flask_migrate import Migrate
import requests
import json
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
import tempfile
import zipfile
import shutil
from flask_socketio import SocketIO, emit, join_room, leave_room

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///healthcare_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth2 config
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth2 client
client = WebApplicationClient(GOOGLE_CLIENT_ID)

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    name = db.Column(db.String(100))
    role = db.Column(db.String(20))  # 'patient', 'doctor', 'nurse'
    profile_image = db.Column(db.String(200))  # Store the path to the profile image
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    medical_history = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    allergies = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

# Care Plan model
class CarePlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    diagnosis = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    goals = db.Column(db.Text, nullable=False)
    interventions = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, pending, completed
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Relationship with Patient
    patient = db.relationship('Patient', backref=db.backref('care_plans', lazy=True))
    # Relationship with Goals
    patient_goals = db.relationship('Goal', backref='care_plan', lazy=True)

# Goal model
class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    care_plan_id = db.Column(db.Integer, db.ForeignKey('care_plan.id'), nullable=False)
    target_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Patient
    patient = db.relationship('Patient', backref=db.backref('goals', lazy=True))

# Activity model
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    care_plan_id = db.Column(db.Integer, db.ForeignKey('care_plan.id'), nullable=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=True)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer)  # Duration in minutes
    activity_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    doctor_name = db.Column(db.String(100))
    enable_reminder = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, in_progress, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = db.relationship('Patient', backref=db.backref('activities', lazy=True))
    care_plan = db.relationship('CarePlan', backref=db.backref('activities', lazy=True))
    goal = db.relationship('Goal', backref=db.backref('activities', lazy=True))

    def __repr__(self):
        return f'<Activity {self.title} for Patient {self.patient_id}>'

    @property
    def formatted_date(self):
        return self.scheduled_date.strftime('%Y-%m-%d') if self.scheduled_date else 'No date set'

    @property
    def formatted_time(self):
        return self.scheduled_date.strftime('%I:%M %p') if self.scheduled_date else 'No time set'

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy=True))

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.recipient_id}>'

# UserSettings model
class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email_notifications = db.Column(db.Boolean, default=True)
    app_notifications = db.Column(db.Boolean, default=True)
    appointment_reminders = db.Column(db.Boolean, default=True)
    two_factor_auth = db.Column(db.String(20), default='disabled')
    data_encryption = db.Column(db.Boolean, default=False)
    theme = db.Column(db.String(20), default='light')
    font_size = db.Column(db.String(20), default='medium')
    data_retention = db.Column(db.Integer, default=90)
    auto_backup = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('settings', uselist=False))

# Initialize database tables
with app.app_context():
    db.create_all()
    # Create a test user if none exists
    if not User.query.first():
        test_user = User(
            email='test@example.com',
            name='Test User',
            role='doctor'
        )
        test_user.set_password('password')
        db.session.add(test_user)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        emit('status', {'user_id': current_user.id, 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')
        emit('status', {'user_id': current_user.id, 'status': 'offline'}, broadcast=True)

@socketio.on('typing')
def handle_typing(data):
    recipient_id = data.get('recipient_id')
    emit('typing', {
        'user_id': current_user.id,
        'name': current_user.name
    }, room=f'user_{recipient_id}')

@socketio.on('message')
def handle_message(data):
    recipient_id = data.get('recipient_id')
    content = data.get('content')
    
    if not recipient_id or not content:
        print('Invalid message data:', data)
        return {'error': 'Invalid message data'}
    
    try:
        # Check if recipient exists
        recipient = User.query.get(recipient_id)
        if not recipient:
            return {'error': 'Recipient not found'}

        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            content=content
        )
        db.session.add(message)
        db.session.commit()
        
        message_data = {
            'id': message.id,
            'sender_id': message.sender_id,
            'recipient_id': message.recipient_id,
            'content': message.content,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Emit to sender
        emit('new_message', message_data, room=f'user_{current_user.id}')
        
        # Emit to recipient
        emit('new_message', message_data, room=f'user_{recipient_id}')
        
        print(f'Message sent from {current_user.id} to {recipient_id}: {content}')
        return {'success': True}
    except Exception as e:
        print('Error sending message:', str(e))
        db.session.rollback()
        return {'error': str(e)}

@socketio.on('message_read')
def handle_message_read(data):
    message_id = data.get('message_id')
    message = Message.query.get(message_id)
    
    if message and message.recipient_id == current_user.id:
        message.read_at = datetime.utcnow()
        db.session.commit()
        
        emit('message_read', {
            'message_id': message_id
        }, room=f'user_{message.sender_id}')

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # Input validation
        if not name or not email or not password or not role:
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))

        # Create new user
        new_user = User(
            name=name,
            email=email,
            role=role
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/google-login')
def google_login():
    # Find out what URL to hit for Google login
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@app.route('/google-login/callback')
def google_callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    # Prepare and send request to get tokens
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens
    client.parse_request_body_response(json.dumps(token_response.json()))
    
    # Now that we have tokens, let's find and hit URL
    # from Google that gives you user's profile information
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        users_name = userinfo_response.json()["given_name"]
        
        # Check if user exists, if not create new user
        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(
                id=unique_id,
                name=users_name,
                email=users_email,
                role='patient'  # Default role
            )
            db.session.add(user)
            db.session.commit()
        
        # Begin user session
        login_user(user)
        return redirect(url_for('dashboard'))
    else:
        return "User email not available or not verified by Google.", 400

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get total counts from database
    total_patients = Patient.query.count()
    total_care_plans = CarePlan.query.count()
    total_messages = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
    ).count()
    total_appointments = Activity.query.filter_by(activity_type='appointment').count()
    
    return render_template('dashboard.html',
        total_patients=total_patients,
        total_care_plans=total_care_plans,
        total_messages=total_messages,
        total_appointments=total_appointments
    )

@app.route('/patients')
@login_required
def patients():
    try:
        # Get search and filter parameters
        search_term = request.args.get('search', '').lower()
        gender_filter = request.args.get('gender', 'all')
        age_filter = request.args.get('age', 'all')
        patient_id = request.args.get('patient_id', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of patients per page
        
        # If patient_id is provided, get that specific patient
        if patient_id:
            patient = Patient.query.get_or_404(patient_id)
            # Get patient's care plans
            care_plans = CarePlan.query.filter_by(patient_id=patient_id).all()
            # Get patient's activities
            activities = Activity.query.filter_by(patient_id=patient_id).order_by(Activity.scheduled_date.desc()).all()
            # Get patient's goals
            goals = Goal.query.filter_by(patient_id=patient_id).all()
            
            return render_template('patient_details.html',
                patient=patient,
                care_plans=care_plans,
                activities=activities,
                goals=goals
            )
        
        # Base query for patient list
        query = Patient.query
        
        # Apply search
        if search_term:
            query = query.filter(
                db.or_(
                    Patient.first_name.ilike(f'%{search_term}%'),
                    Patient.last_name.ilike(f'%{search_term}%'),
                    Patient.email.ilike(f'%{search_term}%'),
                    Patient.phone.ilike(f'%{search_term}%')
                )
            )
        
        # Apply gender filter
        if gender_filter != 'all':
            query = query.filter(Patient.gender == gender_filter)
        
        # Apply age filter
        if age_filter != 'all':
            today = datetime.now().date()
            if age_filter == '0-18':
                query = query.filter(Patient.date_of_birth >= today - timedelta(days=18*365))
            elif age_filter == '19-30':
                query = query.filter(
                    Patient.date_of_birth < today - timedelta(days=18*365),
                    Patient.date_of_birth >= today - timedelta(days=30*365)
                )
            elif age_filter == '31-50':
                query = query.filter(
                    Patient.date_of_birth < today - timedelta(days=30*365),
                    Patient.date_of_birth >= today - timedelta(days=50*365)
                )
            elif age_filter == '50+':
                query = query.filter(Patient.date_of_birth < today - timedelta(days=50*365))
        
        # Get paginated patients
        pagination = query.order_by(Patient.first_name).paginate(page=page, per_page=per_page, error_out=False)
        patients_list = pagination.items
        
        return render_template('patients.html', 
            patients=patients_list,
            pagination=pagination,
            search_term=search_term,
            gender_filter=gender_filter,
            age_filter=age_filter,
            now=datetime.now
        )
    except Exception as e:
        print(f"Error in patients route: {str(e)}")
        return render_template('patients.html', 
            patients=[],
            pagination=None,
            search_term='',
            gender_filter='all',
            age_filter='all',
            now=datetime.now,
            error="An error occurred while loading patients."
        )

@app.route('/add-patient', methods=['POST'])
@login_required
def add_patient():
    try:
        # Print form data for debugging
        print("Received form data:", request.form)
        print("Form data types:", {k: type(v) for k, v in request.form.items()})
        
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'phone']
        for field in required_fields:
            if not request.form.get(field):
                print(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'The field {field} is required.'
                })

        # Convert date string to Python date object
        try:
            date_str = request.form.get('date_of_birth')
            print(f"Date string received: {date_str}")
            if not date_str:
                return jsonify({
                    'success': False,
                    'message': 'Date of birth is required.'
                })
            date_of_birth = datetime.strptime(date_str, '%Y-%m-%d').date()
            print(f"Converted date: {date_of_birth}")
        except ValueError as ve:
            print(f"Date conversion error: {str(ve)}")
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD format.'
            })
        
        # Create new patient from form data
        try:
            new_patient = Patient(
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                date_of_birth=date_of_birth,
                gender=request.form.get('gender'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                address=request.form.get('address'),
                emergency_contact=request.form.get('emergency_contact'),
                emergency_phone=request.form.get('emergency_phone'),
                medical_history=request.form.get('medical_history'),
                current_medications=request.form.get('current_medications'),
                allergies=request.form.get('allergies')
            )
            
            print("Created patient object:", new_patient.__dict__)
            
            db.session.add(new_patient)
            db.session.commit()
            print("Successfully added patient to database")
            
            # Flash a success message
            flash('Patient added successfully!', 'success')
            
            return jsonify({
                'success': True,
                'message': 'Patient added successfully',
                'redirect_url': url_for('patients')
            })
        except Exception as db_error:
            db.session.rollback()
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Database error occurred while adding patient: {str(db_error)}'
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred while adding the patient: {str(e)}'
        })

@app.route('/messages')
@login_required
def messages():
    # Get all users except current user
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('messages.html', users=users)

@app.route('/care-plans')
@login_required
def care_plans():
    try:
        # Get search and filter parameters
        search_term = request.args.get('search', '').lower()
        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of care plans per page
        
        # Base query
        query = CarePlan.query
        
        # Apply search
        if search_term:
            query = query.filter(
                db.or_(
                    CarePlan.title.ilike(f'%{search_term}%'),
                    CarePlan.diagnosis.ilike(f'%{search_term}%'),
                    Patient.first_name.ilike(f'%{search_term}%'),
                    Patient.last_name.ilike(f'%{search_term}%')
                )
            )
        
        # Apply status filter
        if status_filter != 'all':
            query = query.filter(CarePlan.status == status_filter)
        
        # Get paginated care plans
        pagination = query.order_by(CarePlan.start_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
        care_plans_list = pagination.items
        
        # Get all patients for the add care plan form
        patients = Patient.query.order_by(Patient.first_name).all()
        
        return render_template('care_plans.html', 
            patients=patients,
            care_plans=care_plans_list,
            pagination=pagination,
            search_term=search_term,
            status_filter=status_filter
        )
    except Exception as e:
        print(f"Error in care_plans route: {str(e)}")
        return render_template('care_plans.html', 
            patients=[],
            care_plans=[],
            pagination=None,
            search_term='',
            status_filter='all',
            error="An error occurred while loading care plans."
        )

@app.route('/add-care-plan', methods=['POST'])
@login_required
def add_care_plan():
    try:
        # Print form data for debugging
        print("Received form data:", request.form)
        
        # Validate required fields
        required_fields = ['patient_id', 'title', 'diagnosis', 'start_date', 'end_date', 'goals', 'interventions']
        for field in required_fields:
            if not request.form.get(field):
                print(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'The field {field} is required.'
                })

        # Convert date strings to Python date objects
        try:
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            # Validate that end date is after start date
            if end_date <= start_date:
                return jsonify({
                    'success': False,
                    'message': 'End date must be after start date.'
                })
                
        except ValueError as ve:
            print(f"Date conversion error: {str(ve)}")
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD format.'
            })
        
        # Create new care plan
        new_care_plan = CarePlan(
            patient_id=request.form.get('patient_id'),
            title=request.form.get('title'),
            diagnosis=request.form.get('diagnosis'),
            start_date=start_date,
            end_date=end_date,
            goals=request.form.get('goals'),
            interventions=request.form.get('interventions'),
            notes=request.form.get('notes'),
            status='active'
        )
        
        print("Created care plan object:", new_care_plan.__dict__)
        
        try:
            db.session.add(new_care_plan)
            db.session.commit()
            print("Successfully added care plan to database")
            
            # Flash a success message
            flash('Care plan created successfully!', 'success')
            
            return jsonify({
                'success': True,
                'message': 'Care plan created successfully',
                'redirect_url': url_for('care_plans')
            })
        except Exception as db_error:
            db.session.rollback()
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Database error occurred while creating care plan: {str(db_error)}'
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred while creating the care plan: {str(e)}'
        })

@app.route('/goals')
@login_required
def goals():
    patients = Patient.query.all()
    goals_list = Goal.query.all()
    return render_template('goals.html', patients=patients, goals=goals_list)

@app.route('/goals/<int:goal_id>')
@login_required
def view_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    return jsonify({
        'id': goal.id,
        'title': goal.title,
        'description': goal.description,
        'patient_name': f"{goal.patient.first_name} {goal.patient.last_name}",
        'patient_id': goal.patient_id,
        'care_plan_title': goal.care_plan.title,
        'care_plan_id': goal.care_plan_id,
        'target_date': goal.target_date.strftime('%Y-%m-%d'),
        'status': goal.status,
        'created_at': goal.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/goals/<int:goal_id>/edit', methods=['POST'])
@login_required
def edit_goal(goal_id):
    try:
        goal = Goal.query.get_or_404(goal_id)
        
        # Print form data for debugging
        print("Received form data:", request.form)
        
        # Validate required fields
        required_fields = ['title', 'description', 'target_date', 'status']
        for field in required_fields:
            if not request.form.get(field):
                print(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'The field {field} is required.'
                })

        # Convert date string to Python date object
        try:
            target_date = datetime.strptime(request.form.get('target_date'), '%Y-%m-%d').date()
        except ValueError as ve:
            print(f"Date conversion error: {str(ve)}")
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD format.'
            })
        
        # Update goal
        goal.title = request.form.get('title')
        goal.description = request.form.get('description')
        goal.target_date = target_date
        goal.status = request.form.get('status')
        
        try:
            db.session.commit()
            print("Successfully updated goal")
            
            return jsonify({
                'success': True,
                'message': 'Goal updated successfully',
                'redirect_url': url_for('goals')
            })
        except Exception as db_error:
            db.session.rollback()
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Database error occurred while updating goal: {str(db_error)}'
            })
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred while updating the goal: {str(e)}'
        })

@app.route('/add-goal', methods=['POST'])
@login_required
def add_goal():
    try:
        # Print form data for debugging
        print("Received form data:", request.form)
        
        # Validate required fields
        required_fields = ['patient_id', 'care_plan_id', 'title', 'description', 'target_date']
        for field in required_fields:
            if not request.form.get(field):
                print(f"Missing required field: {field}")
                return jsonify({
                    'success': False,
                    'message': f'The field {field} is required.'
                })

        # Convert date string to Python date object
        try:
            target_date = datetime.strptime(request.form.get('target_date'), '%Y-%m-%d').date()
        except ValueError as ve:
            print(f"Date conversion error: {str(ve)}")
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Please use YYYY-MM-DD format.'
            })
        
        # Create new goal
        new_goal = Goal(
            patient_id=request.form.get('patient_id'),
            care_plan_id=request.form.get('care_plan_id'),
            title=request.form.get('title'),
            description=request.form.get('description'),
            target_date=target_date,
            status='pending'
        )
        
        print("Created goal object:", new_goal.__dict__)
        
        try:
            db.session.add(new_goal)
            db.session.commit()
            print("Successfully added goal to database")
            
            return jsonify({
                'success': True,
                'message': 'Goal created successfully',
                'redirect_url': url_for('goals')
            })
        except Exception as db_error:
            db.session.rollback()
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Database error occurred while creating goal: {str(db_error)}'
            })
            
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred while creating the goal: {str(e)}'
        })

@app.route('/activities')
@login_required
def activities():
    try:
        # Get current month for calendar
        current_month = datetime.now()
        
        # Get search and filter parameters
        search_term = request.args.get('search', '').lower()
        activity_type = request.args.get('type', 'all')
        status_filter = request.args.get('status', 'all')
        
        # Base query
        query = Activity.query
        
        # Apply filters
        if activity_type != 'all':
            query = query.filter(Activity.activity_type == activity_type)
        if status_filter != 'all':
            query = query.filter(Activity.status == status_filter)
        if search_term:
            query = query.filter(
                db.or_(
                    Activity.title.ilike(f'%{search_term}%'),
                    Activity.description.ilike(f'%{search_term}%'),
                    Activity.doctor_name.ilike(f'%{search_term}%'),
                    Activity.location.ilike(f'%{search_term}%')
                )
            )
        
        # Get all activities or filter by status
        all_activities = query.order_by(Activity.scheduled_date.desc()).all()
        
        # Get activities grouped by date for calendar
        activities_by_date = {}
        for activity in all_activities:
            date_key = activity.scheduled_date.strftime('%Y-%m-%d')
            if date_key not in activities_by_date:
                activities_by_date[date_key] = []
            activities_by_date[date_key].append({
                'id': activity.id,
                'title': activity.title,
                'time': activity.scheduled_date.strftime('%I:%M %p'),
                'type': activity.activity_type,
                'doctor_name': activity.doctor_name,
                'location': activity.location,
                'status': activity.status
            })
        
        # Get all patients for the schedule activity form
        patients = Patient.query.order_by(Patient.first_name).all()
        
        # Get all doctors for the schedule activity form
        doctors = User.query.filter_by(role='doctor').all()
        
        return render_template('activities.html', 
            current_month=current_month,
            activities_by_date=activities_by_date,
            all_activities=all_activities,
            patients=patients,
            doctors=doctors,
            status_filter=status_filter or 'all',
            activity_type=activity_type,
            search_term=search_term
        )
    except Exception as e:
        print(f"Error in activities route: {str(e)}")
        return render_template('activities.html', 
            current_month=datetime.now(),
            activities_by_date={},
            all_activities=[],
            patients=[],
            doctors=[],
            status_filter='all',
            activity_type='all',
            search_term='',
            error="An error occurred while loading activities."
        )

@app.route('/add_activity', methods=['POST'])
@login_required
def add_activity():
    try:
        print("=== Form Submission Debug ===")
        print("Request Method:", request.method)
        print("Request Content Type:", request.content_type)
        print("Request Form Data:", request.form)
        print("Request JSON Data:", request.get_json(silent=True))
        
        # Get form data
        patient_id = request.form.get('patient_id')
        care_plan_id = request.form.get('care_plan_id')
        goal_id = request.form.get('goal_id')
        title = request.form.get('title')
        description = request.form.get('description')
        activity_date = request.form.get('activity_date')
        activity_time = request.form.get('activity_time')
        duration = request.form.get('duration')
        activity_type = request.form.get('activity_type')
        location = request.form.get('location')
        doctor_name = request.form.get('doctor_name')
        enable_reminder = request.form.get('enable_reminder', 'true').lower() == 'true'
        status = request.form.get('status', 'pending')

        # Debug print all form fields
        print("\nForm fields:")
        print(f"patient_id: {patient_id}")
        print(f"care_plan_id: {care_plan_id}")
        print(f"goal_id: {goal_id}")
        print(f"title: {title}")
        print(f"description: {description}")
        print(f"activity_date: {activity_date}")
        print(f"activity_time: {activity_time}")
        print(f"duration: {duration}")
        print(f"activity_type: {activity_type}")
        print(f"location: {location}")
        print(f"doctor_name: {doctor_name}")
        print(f"enable_reminder: {enable_reminder}")
        print(f"status: {status}")

        # Validate required fields
        if not all([patient_id, care_plan_id, title, description, activity_date, activity_time, duration, activity_type, location]):
            missing_fields = []
            if not patient_id: missing_fields.append('patient_id')
            if not care_plan_id: missing_fields.append('care_plan_id')
            if not title: missing_fields.append('title')
            if not description: missing_fields.append('description')
            if not activity_date: missing_fields.append('activity_date')
            if not activity_time: missing_fields.append('activity_time')
            if not duration: missing_fields.append('duration')
            if not activity_type: missing_fields.append('activity_type')
            if not location: missing_fields.append('location')
            
            print(f"\nMissing required fields: {missing_fields}")
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Convert date and time strings to datetime
        try:
            scheduled_date = datetime.strptime(f"{activity_date} {activity_time}", "%Y-%m-%d %H:%M")
            duration = int(duration)  # Convert duration to integer
            print(f"\nConverted scheduled_date: {scheduled_date}")
            print(f"Converted duration: {duration}")
        except ValueError as e:
            print(f"\nDate/time conversion error: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Invalid date, time, or duration format.'
            }), 400

        # Create new activity
        new_activity = Activity(
            patient_id=patient_id,
            care_plan_id=care_plan_id,
            goal_id=goal_id if goal_id else None,
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            duration=duration,
            activity_type=activity_type,
            location=location,
            doctor_name=doctor_name,
            enable_reminder=enable_reminder,
            status=status
        )

        print("\nCreated activity object:", new_activity.__dict__)

        # Add to database
        db.session.add(new_activity)
        db.session.commit()
        print("\nSuccessfully added activity to database")
        
        return jsonify({
            'success': True,
            'message': 'Activity scheduled successfully!',
            'activity': {
                'id': new_activity.id,
                'title': new_activity.title,
                'scheduled_date': new_activity.scheduled_date.isoformat(),
                'status': new_activity.status
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"\nError scheduling activity: {str(e)}")
        print("Error type:", type(e).__name__)
        import traceback
        print("Traceback:", traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'An error occurred while scheduling the activity: {str(e)}'
        }), 500

@app.route('/analytics')
@login_required
def analytics():
    try:
        # Get real data from database
        total_patients = Patient.query.count()
        total_care_plans = CarePlan.query.count()
        active_care_plans = CarePlan.query.filter_by(status='active').count()

        # Calculate treatment outcomes based on care plan status
        treatment_outcomes = {
            'improved': CarePlan.query.filter_by(status='completed').count(),
            'unchanged': CarePlan.query.filter_by(status='active').count(),
            'deteriorated': CarePlan.query.filter_by(status='pending').count()
        }

        # Calculate adherence rates from activities
        activities = Activity.query.all()
        adherence_data = {
            'labels': ['Medication', 'Appointments', 'Exercise', 'Diet'],
            'values': [0, 0, 0, 0]  # Will be updated by API
        }

        return render_template('analytics.html',
                             treatment_outcomes=treatment_outcomes,
                             adherence_labels=adherence_data['labels'],
                             adherence_values=adherence_data['values'],
                             total_patients=total_patients,
                             total_care_plans=total_care_plans,
                             active_care_plans=active_care_plans)

    except Exception as e:
        print(f"Error in analytics route: {str(e)}")
        return render_template('analytics.html',
                             treatment_outcomes={'improved': 0, 'unchanged': 0, 'deteriorated': 0},
                             adherence_labels=['Medication', 'Appointments', 'Exercise', 'Diet'],
                             adherence_values=[0, 0, 0, 0],
                             total_patients=0,
                             total_care_plans=0,
                             active_care_plans=0)

@app.route('/api/analytics/treatment-outcomes')
@login_required
def get_treatment_outcomes():
    try:
        outcomes = {
            'improved': CarePlan.query.filter_by(status='completed').count(),
            'unchanged': CarePlan.query.filter_by(status='active').count(),
            'deteriorated': CarePlan.query.filter_by(status='pending').count()
        }
        return jsonify(outcomes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/adherence')
@login_required
def get_adherence_data():
    try:
        # Get all activities
        activities = Activity.query.all()
        
        # Initialize counters for each activity type
        activity_counts = {
            'Medication': {'total': 0, 'completed': 0},
            'Appointments': {'total': 0, 'completed': 0},
            'Exercise': {'total': 0, 'completed': 0},
            'Diet': {'total': 0, 'completed': 0}
        }
        
        # Count activities by type and status
        for activity in activities:
            if activity.activity_type in activity_counts:
                activity_counts[activity.activity_type]['total'] += 1
                if activity.status == 'completed':
                    activity_counts[activity.activity_type]['completed'] += 1
        
        # Calculate adherence rates
        adherence_data = {
            'labels': list(activity_counts.keys()),
            'values': [
                round((counts['completed'] / counts['total'] * 100) if counts['total'] > 0 else 0)
                for counts in activity_counts.values()
            ]
        }
        
        return jsonify(adherence_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/patient-progress')
@login_required
def get_patient_progress():
    try:
        # Get care plans grouped by month
        care_plans = db.session.query(
            func.strftime('%Y-%m', CarePlan.created_at).label('month'),
            func.count(CarePlan.id).label('count')
        ).group_by('month').order_by('month').all()
        
        progress_data = {
            'labels': [plan.month for plan in care_plans],
            'values': [plan.count for plan in care_plans]
        }
        
        return jsonify(progress_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/care-plan-distribution')
@login_required
def get_care_plan_distribution():
    try:
        # Get care plans grouped by diagnosis
        care_plans = db.session.query(
            CarePlan.diagnosis,
            func.count(CarePlan.id).label('count')
        ).group_by(CarePlan.diagnosis).all()
        
        distribution_data = {
            'labels': [plan.diagnosis for plan in care_plans],
            'values': [plan.count for plan in care_plans]
        }
        
        return jsonify(distribution_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/health-trends')
@login_required
def get_health_trends():
    try:
        # Get activities grouped by month and type
        activities = db.session.query(
            func.strftime('%Y-%m', Activity.scheduled_date).label('month'),
            Activity.activity_type,
            func.count(Activity.id).label('count')
        ).group_by('month', Activity.activity_type).order_by('month').all()
        
        # Organize data by activity type
        activity_types = set(activity.activity_type for activity in activities)
        months = sorted(set(activity.month for activity in activities))
        
        trends_data = {
            'labels': months,
            'datasets': [
                {
                    'label': activity_type,
                    'data': [
                        next((a.count for a in activities if a.month == month and a.activity_type == activity_type), 0)
                        for month in months
                    ]
                }
                for activity_type in activity_types
            ]
        }
        
        return jsonify(trends_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/settings')
@login_required
def settings():
    user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()
    return render_template('settings.html', settings=user_settings)

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    try:
        data = request.get_json()
        user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        
        if not user_settings:
            user_settings = UserSettings(user_id=current_user.id)
            db.session.add(user_settings)
        
        # Update settings
        for key, value in data.items():
            if hasattr(user_settings, key):
                setattr(user_settings, key, value)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/export-data')
@login_required
def export_data():
    try:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Export user data
        user_data = {
            'profile': {
                'name': current_user.name,
                'email': current_user.email,
                'role': current_user.role
            },
            'settings': {
                'email_notifications': current_user.settings.email_notifications,
                'app_notifications': current_user.settings.app_notifications,
                'theme': current_user.settings.theme,
                'font_size': current_user.settings.font_size
            }
        }
        
        # Write user data to JSON file
        with open(os.path.join(temp_dir, 'user_data.json'), 'w') as f:
            json.dump(user_data, f, indent=2)
        
        # Create ZIP file
        zip_path = os.path.join(temp_dir, 'carenest-data-export.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != 'carenest-data-export.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Send the ZIP file
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='carenest-data-export.zip'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)

@app.route('/api/patient/<int:patient_id>/care-plans')
@login_required
def get_patient_care_plans(patient_id):
    try:
        care_plans = CarePlan.query.filter_by(patient_id=patient_id).all()
        return jsonify([{
            'id': plan.id,
            'title': plan.title
        } for plan in care_plans])
    except Exception as e:
        print(f"Error fetching care plans: {str(e)}")
        return jsonify([]), 500

@app.route('/api/care-plan/<int:care_plan_id>/goals')
@login_required
def get_care_plan_goals(care_plan_id):
    try:
        goals = Goal.query.filter_by(care_plan_id=care_plan_id).all()
        return jsonify([{
            'id': goal.id,
            'title': goal.title
        } for goal in goals])
    except Exception as e:
        print(f"Error fetching goals: {str(e)}")
        return jsonify([]), 500

@app.route('/api/care-plan/<int:care_plan_id>')
@login_required
def get_care_plan(care_plan_id):
    try:
        care_plan = CarePlan.query.get_or_404(care_plan_id)
        return jsonify({
            'id': care_plan.id,
            'patient_id': care_plan.patient_id,
            'patient_name': f"{care_plan.patient.first_name} {care_plan.patient.last_name}",
            'title': care_plan.title,
            'diagnosis': care_plan.diagnosis,
            'start_date': care_plan.start_date.strftime('%Y-%m-%d'),
            'end_date': care_plan.end_date.strftime('%Y-%m-%d'),
            'goals': care_plan.goals,
            'interventions': care_plan.interventions,
            'notes': care_plan.notes,
            'status': care_plan.status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/care-plan/<int:care_plan_id>', methods=['PUT'])
@login_required
def update_care_plan(care_plan_id):
    try:
        care_plan = CarePlan.query.get_or_404(care_plan_id)
        
        # Update care plan fields
        care_plan.title = request.form.get('title')
        care_plan.diagnosis = request.form.get('diagnosis')
        care_plan.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        care_plan.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        care_plan.goals = request.form.get('goals')
        care_plan.interventions = request.form.get('interventions')
        care_plan.notes = request.form.get('notes')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Care plan updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/care-plan/<int:care_plan_id>', methods=['DELETE'])
@login_required
def delete_care_plan(care_plan_id):
    try:
        care_plan = CarePlan.query.get_or_404(care_plan_id)
        db.session.delete(care_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Care plan deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/patient/<int:patient_id>')
@login_required
def get_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        return jsonify({
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d'),
            'gender': patient.gender,
            'phone': patient.phone,
            'email': patient.email,
            'address': patient.address,
            'emergency_contact': patient.emergency_contact,
            'emergency_phone': patient.emergency_phone,
            'medical_history': patient.medical_history,
            'current_medications': patient.current_medications,
            'allergies': patient.allergies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/patient/<int:patient_id>', methods=['PUT'])
@login_required
def update_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Update patient fields
        patient.first_name = request.form.get('first_name')
        patient.last_name = request.form.get('last_name')
        patient.date_of_birth = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
        patient.gender = request.form.get('gender')
        patient.phone = request.form.get('phone')
        patient.email = request.form.get('email')
        patient.address = request.form.get('address')
        patient.emergency_contact = request.form.get('emergency_contact')
        patient.emergency_phone = request.form.get('emergency_phone')
        patient.medical_history = request.form.get('medical_history')
        patient.current_medications = request.form.get('current_medications')
        patient.allergies = request.form.get('allergies')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Patient updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/patient/<int:patient_id>', methods=['DELETE'])
@login_required
def delete_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        db.session.delete(patient)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Patient deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/schedule')
@login_required
def schedule():
    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # Get today's activities with non-null scheduled_date
        todays_activities = Activity.query.filter(
            db.func.date(Activity.scheduled_date) == today,
            Activity.scheduled_date.isnot(None)
        ).order_by(Activity.scheduled_date).all()
        
        # Get upcoming activities with non-null scheduled_date
        upcoming_activities = Activity.query.filter(
            db.func.date(Activity.scheduled_date) >= tomorrow,
            Activity.scheduled_date.isnot(None)
        ).order_by(Activity.scheduled_date).all()
        
        # Get activities for the calendar
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        calendar_activities = Activity.query.filter(
            Activity.scheduled_date.between(start_of_month, end_of_month)
        ).all()
        
        # Group activities by date for the calendar
        activities_by_date = {}
        for activity in calendar_activities:
            date_key = activity.scheduled_date.date().isoformat()  # Convert date to string
            if date_key not in activities_by_date:
                activities_by_date[date_key] = []
            activities_by_date[date_key].append({
                'id': activity.id,
                'title': activity.title,
                'time': activity.scheduled_date.strftime('%I:%M %p'),
                'doctor_name': activity.doctor_name,
                'location': activity.location
            })
        
        return render_template('schedule.html', 
                             todays_activities=todays_activities,
                             upcoming_activities=upcoming_activities,
                             activities_by_date=activities_by_date,
                             current_month=start_of_month)
    except Exception as e:
        print(f"Error in schedule route: {str(e)}")
        return render_template('schedule.html', 
                             todays_activities=[],
                             upcoming_activities=[],
                             activities_by_date={},
                             current_month=datetime.now(),
                             error="An error occurred while loading the schedule.")

@app.route('/api/activity', methods=['POST'])
@login_required
def create_activity():
    try:
        data = request.get_json()
        if not data.get('title') or not data.get('scheduled_date'):
            return jsonify({
                'success': False,
                'message': 'Title and scheduled date are required.'
            }), 400

        # Get the first patient from the database (temporary solution)
        patient = Patient.query.first()
        if not patient:
            return jsonify({
                'success': False,
                'message': 'No patients found in the system.'
            }), 400

        new_activity = Activity(
            title=data['title'],
            description=data.get('description', ''),
            scheduled_date=datetime.fromisoformat(data['scheduled_date'].replace('Z', '+00:00')),
            patient_id=patient.id,  # Using the first patient's ID
            activity_type='appointment',
            location=data.get('location'),
            doctor_name=data.get('doctor_name'),
            enable_reminder=data.get('enable_reminder', True)
        )
        db.session.add(new_activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Appointment scheduled successfully',
            'activity': {
                'id': new_activity.id,
                'title': new_activity.title,
                'scheduled_date': new_activity.scheduled_date.isoformat(),
                'doctor_name': new_activity.doctor_name,
                'location': new_activity.location
            }
        })
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Invalid date format: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Error creating activity: {str(e)}")  # Add debug print
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/activity/<int:activity_id>', methods=['GET'])
@login_required
def get_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        return jsonify({
            'success': True,
            'activity': {
                'id': activity.id,
                'title': activity.title,
                'description': activity.description,
                'scheduled_date': activity.scheduled_date.isoformat() if activity.scheduled_date else None,
                'formatted_date': activity.formatted_date,
                'formatted_time': activity.formatted_time,
                'doctor_name': activity.doctor_name,
                'location': activity.location,
                'duration': activity.duration,
                'activity_type': activity.activity_type,
                'status': activity.status,
                'patient_id': activity.patient_id,
                'care_plan_id': activity.care_plan_id,
                'goal_id': activity.goal_id,
                'patient': {
                    'id': activity.patient.id,
                    'first_name': activity.patient.first_name,
                    'last_name': activity.patient.last_name
                } if activity.patient else None,
                'care_plan': {
                    'id': activity.care_plan.id,
                    'title': activity.care_plan.title
                } if activity.care_plan else None,
                'goal': {
                    'id': activity.goal.id,
                    'title': activity.goal.title
                } if activity.goal else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/activity/<int:activity_id>', methods=['PUT'])
@login_required
def update_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        data = request.get_json()
        
        if not data.get('title') or not data.get('scheduled_date'):
            return jsonify({
                'success': False,
                'message': 'Title and scheduled date are required.'
            }), 400
        
        # Update all fields
        activity.title = data['title']
        activity.description = data.get('description', '')
        activity.scheduled_date = datetime.fromisoformat(data['scheduled_date'])
        activity.duration = data.get('duration')
        activity.activity_type = data.get('activity_type')
        activity.location = data.get('location')
        activity.doctor_name = data.get('doctor_name')
        activity.status = data.get('status', activity.status)
        activity.patient_id = data.get('patient_id')
        activity.care_plan_id = data.get('care_plan_id')
        activity.goal_id = data.get('goal_id')
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Activity updated successfully'})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/activity/<int:activity_id>', methods=['DELETE'])
@login_required
def delete_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        db.session.delete(activity)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Activity deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/patients')
@login_required
def get_patients():
    try:
        patients = Patient.query.all()
        return jsonify([{
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name
        } for patient in patients])
    except Exception as e:
        return jsonify([]), 500

@app.route('/api/activities/export')
@login_required
def export_activities():
    try:
        # Get filter parameters
        activity_type = request.args.get('type', 'all')
        status_filter = request.args.get('status', 'all')
        search_term = request.args.get('search', '').lower()
        
        # Base query
        query = Activity.query
        
        # Apply filters
        if activity_type != 'all':
            query = query.filter(Activity.activity_type == activity_type)
        if status_filter != 'all':
            query = query.filter(Activity.status == status_filter)
        if search_term:
            query = query.filter(
                db.or_(
                    Activity.title.ilike(f'%{search_term}%'),
                    Activity.description.ilike(f'%{search_term}%'),
                    Activity.doctor_name.ilike(f'%{search_term}%'),
                    Activity.location.ilike(f'%{search_term}%')
                )
            )
        
        # Get activities
        activities = query.order_by(Activity.scheduled_date.desc()).all()
        
        # Format data for export
        export_data = []
        for activity in activities:
            export_data.append({
                'title': activity.title,
                'description': activity.description,
                'date': activity.scheduled_date.strftime('%Y-%m-%d'),
                'time': activity.scheduled_date.strftime('%I:%M %p'),
                'type': activity.activity_type,
                'doctor': activity.doctor_name,
                'location': activity.location,
                'status': activity.status,
                'patient': f"{activity.patient.first_name} {activity.patient.last_name}" if activity.patient else '',
                'care_plan': activity.care_plan.title if activity.care_plan else '',
                'goal': activity.goal.title if activity.goal else ''
            })
        
        return jsonify({
            'success': True,
            'data': export_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/patients/export')
@login_required
def export_patients():
    try:
        # Get filter parameters
        search_term = request.args.get('search', '').lower()
        gender_filter = request.args.get('gender', 'all')
        age_filter = request.args.get('age', 'all')
        
        # Base query
        query = Patient.query
        
        # Apply search
        if search_term:
            query = query.filter(
                db.or_(
                    Patient.first_name.ilike(f'%{search_term}%'),
                    Patient.last_name.ilike(f'%{search_term}%'),
                    Patient.email.ilike(f'%{search_term}%'),
                    Patient.phone.ilike(f'%{search_term}%')
                )
            )
        
        # Apply gender filter
        if gender_filter != 'all':
            query = query.filter(Patient.gender == gender_filter)
        
        # Apply age filter
        if age_filter != 'all':
            today = datetime.now().date()
            if age_filter == '0-18':
                query = query.filter(Patient.date_of_birth >= today - timedelta(days=18*365))
            elif age_filter == '19-30':
                query = query.filter(
                    Patient.date_of_birth < today - timedelta(days=18*365),
                    Patient.date_of_birth >= today - timedelta(days=30*365)
                )
            elif age_filter == '31-50':
                query = query.filter(
                    Patient.date_of_birth < today - timedelta(days=30*365),
                    Patient.date_of_birth >= today - timedelta(days=50*365)
                )
            elif age_filter == '50+':
                query = query.filter(Patient.date_of_birth < today - timedelta(days=50*365))
        
        # Get patients
        patients = query.order_by(Patient.first_name).all()
        
        # Format data for export
        export_data = []
        for patient in patients:
            age = (datetime.now().date() - patient.date_of_birth).days // 365
            export_data.append({
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d'),
                'age': age,
                'gender': patient.gender,
                'phone': patient.phone,
                'email': patient.email,
                'address': patient.address,
                'emergency_contact': patient.emergency_contact,
                'emergency_phone': patient.emergency_phone,
                'medical_history': patient.medical_history,
                'current_medications': patient.current_medications,
                'allergies': patient.allergies
            })
        
        return jsonify({
            'success': True,
            'data': export_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/activities')
def get_all_activities():
    try:
        activities = Activity.query.all()
        activities_list = []
        for activity in activities:
            activities_list.append({
                'id': activity.id,
                'title': activity.title,
                'description': activity.description,
                'scheduled_date': activity.scheduled_date.isoformat(),
                'duration': activity.duration,
                'activity_type': activity.activity_type,
                'location': activity.location,
                'doctor_name': activity.doctor_name,
                'status': activity.status,
                'patient_id': activity.patient_id,
                'care_plan_id': activity.care_plan_id,
                'goal_id': activity.goal_id,
                'time': activity.scheduled_date.strftime('%I:%M %p'),
                'type': activity.activity_type
            })
        return jsonify({'success': True, 'activities': activities_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/care-plans/export')
@login_required
def export_care_plans():
    try:
        # Get filter parameters
        search_term = request.args.get('search', '').lower()
        status_filter = request.args.get('status', 'all')
        
        # Base query
        query = CarePlan.query
        
        # Apply search
        if search_term:
            query = query.filter(
                db.or_(
                    CarePlan.title.ilike(f'%{search_term}%'),
                    CarePlan.diagnosis.ilike(f'%{search_term}%'),
                    Patient.first_name.ilike(f'%{search_term}%'),
                    Patient.last_name.ilike(f'%{search_term}%')
                )
            )
        
        # Apply status filter
        if status_filter != 'all':
            query = query.filter(CarePlan.status == status_filter)
        
        # Get care plans
        care_plans = query.order_by(CarePlan.start_date.desc()).all()
        
        # Format data for export
        export_data = []
        for care_plan in care_plans:
            export_data.append({
                'patient_name': f"{care_plan.patient.first_name} {care_plan.patient.last_name}",
                'patient_id': care_plan.patient.id,
                'title': care_plan.title,
                'diagnosis': care_plan.diagnosis,
                'start_date': care_plan.start_date.strftime('%Y-%m-%d'),
                'end_date': care_plan.end_date.strftime('%Y-%m-%d'),
                'goals': care_plan.goals,
                'interventions': care_plan.interventions,
                'notes': care_plan.notes,
                'status': care_plan.status
            })
        
        return jsonify({
            'success': True,
            'data': export_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/goals/export')
@login_required
def export_goals():
    try:
        # Get filter parameters
        search_term = request.args.get('search', '').lower()
        status_filter = request.args.get('status', 'all')
        
        # Base query
        query = Goal.query
        
        # Apply search
        if search_term:
            query = query.filter(
                db.or_(
                    Goal.title.ilike(f'%{search_term}%'),
                    Goal.description.ilike(f'%{search_term}%'),
                    Patient.first_name.ilike(f'%{search_term}%'),
                    Patient.last_name.ilike(f'%{search_term}%')
                )
            )
        
        # Apply status filter
        if status_filter != 'all':
            query = query.filter(Goal.status == status_filter)
        
        # Get goals
        goals = query.order_by(Goal.target_date.desc()).all()
        
        # Format data for export
        export_data = []
        for goal in goals:
            export_data.append({
                'title': goal.title,
                'description': goal.description,
                'patient_name': f"{goal.patient.first_name} {goal.patient.last_name}",
                'care_plan_title': goal.care_plan.title,
                'status': goal.status,
                'target_date': goal.target_date.strftime('%Y-%m-%d') if goal.target_date else None
            })
        
        return jsonify({
            'success': True,
            'data': export_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    if 'profile_image' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['profile_image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    try:
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.static_folder, 'uploads', 'profile_images')
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        filename = f"profile_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg"
        filepath = os.path.join(upload_dir, filename)

        # Save the file
        file.save(filepath)

        # Update user's profile image path
        current_user.profile_image = f"/static/uploads/profile_images/{filename}"
        db.session.commit()

        return jsonify({
            'success': True,
            'image_url': current_user.profile_image
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    recipient_id = data.get('recipient_id')
    content = data.get('content')
    if not recipient_id or not content:
        return jsonify({'success': False, 'error': 'Missing recipient or content'}), 400

    # Assuming you have a Message model
    message = Message(sender_id=current_user.id, recipient_id=recipient_id, content=content)
    db.session.add(message)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Message sent!'})

@app.route('/get_messages', methods=['GET'])
@login_required
def get_messages():
    recipient_id = request.args.get('recipient_id')
    if not recipient_id:
        return jsonify({'success': False, 'error': 'Missing recipient'}), 400

    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id)) |
        ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    # Get recipient info
    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({'success': False, 'error': 'Recipient not found'}), 404

    messages_data = [
        {
            'id': m.id,
            'sender_id': m.sender_id,
            'recipient_id': m.recipient_id,
            'content': m.content,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for m in messages
    ]
    return jsonify({
        'success': True,
        'messages': messages_data,
        'recipient_name': recipient.name,
        'recipient_email': recipient.email
    })

@app.route('/get_conversations', methods=['GET'])
@login_required
def get_conversations():
    # Get all unique users that the current user has exchanged messages with
    sent_messages = Message.query.filter_by(sender_id=current_user.id).with_entities(Message.recipient_id).distinct()
    received_messages = Message.query.filter_by(recipient_id=current_user.id).with_entities(Message.sender_id).distinct()
    
    # Combine and get unique user IDs
    user_ids = set([m.recipient_id for m in sent_messages] + [m.sender_id for m in received_messages])
    
    conversations = []
    for user_id in user_ids:
        # Get user info
        user = User.query.get(user_id)
        if not user:
            continue
            
        # Get last message
        last_message = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
            ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        
        if last_message:
            # Count unread messages
            unread_count = Message.query.filter(
                Message.sender_id == user_id,
                Message.recipient_id == current_user.id,
                Message.read_at.is_(None)
            ).count()
            
            conversations.append({
                'user_id': user.id,
                'name': user.name,
                'email': user.email,
                'last_message': last_message.content,
                'last_message_time': last_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'unread': unread_count > 0
            })
    
    # Sort conversations by last message time
    conversations.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    return jsonify({
        'success': True,
        'conversations': conversations
    })

@app.route('/mark_messages_read', methods=['POST'])
@login_required
def mark_messages_read():
    sender_id = request.json.get('sender_id')
    if not sender_id:
        return jsonify({'success': False, 'error': 'Missing sender ID'}), 400

    # Mark all unread messages from this sender as read
    Message.query.filter_by(
        sender_id=sender_id,
        recipient_id=current_user.id,
        read_at=None
    ).update({'read_at': datetime.utcnow()})
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/dashboard/counts')
@login_required
def get_dashboard_counts():
    try:
        # Get total counts from database
        total_patients = Patient.query.count()
        total_care_plans = CarePlan.query.count()
        total_messages = Message.query.filter(
            (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
        ).count()
        total_appointments = Activity.query.filter_by(activity_type='appointment').count()
        
        return jsonify({
            'success': True,
            'total_patients': total_patients,
            'total_care_plans': total_care_plans,
            'total_messages': total_messages,
            'total_appointments': total_appointments
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/quick_actions')
@login_required
def quick_actions():
    return render_template('quick_actions.html')

@app.route('/api/quick-actions/appointments')
@login_required
def get_today_appointments():
    # Get today's appointments count
    today = datetime.now().date()
    appointments = Activity.query.filter(
        Activity.activity_type == 'appointment',
        db.func.date(Activity.scheduled_date) == today
    ).count()
    return jsonify({'count': appointments})

@app.route('/api/quick-actions/messages')
@login_required
def get_unread_messages():
    # Get unread messages count
    unread = Message.query.filter(
        Message.recipient_id == current_user.id,
        Message.read_at.is_(None)
    ).count()
    return jsonify({'count': unread})

@app.route('/api/quick-actions/notifications')
@login_required
def get_notifications():
    try:
        # Get unread notifications count
        notifications = Activity.query.filter(
            Activity.status == 'pending',
            Activity.scheduled_date >= datetime.now(),
            Activity.activity_type.in_(['appointment', 'task', 'reminder'])
        ).count()
        return jsonify({'count': notifications})
    except Exception as e:
        print(f"Error getting notifications count: {str(e)}")
        return jsonify({'count': 0, 'error': str(e)}), 500

@app.route('/api/quick-actions/tasks')
@login_required
def get_pending_tasks():
    try:
        # Get pending tasks count
        tasks = Activity.query.filter(
            Activity.status == 'pending',
            Activity.scheduled_date >= datetime.now(),
            Activity.activity_type == 'task'
        ).count()
        return jsonify({'count': tasks})
    except Exception as e:
        print(f"Error getting tasks count: {str(e)}")
        return jsonify({'count': 0, 'error': str(e)}), 500

@app.route('/api/quick-actions/recent-activity')
@login_required
def get_recent_activity():
    try:
        # Get recent activities (last 10)
        activities = Activity.query.order_by(
            Activity.scheduled_date.desc()
        ).limit(10).all()
        
        return jsonify([{
            'time': activity.scheduled_date.strftime('%H:%M'),
            'description': activity.title,
            'user': activity.doctor_name or 'System',
            'status': activity.status,
            'status_color': {
                'completed': 'success',
                'pending': 'warning',
                'cancelled': 'danger',
                'scheduled': 'info'
            }.get(activity.status, 'secondary')
        } for activity in activities])
    except Exception as e:
        print(f"Error getting recent activities: {str(e)}")
        return jsonify([]), 500

if __name__ == '__main__':
    socketio.run(app, debug=True) 