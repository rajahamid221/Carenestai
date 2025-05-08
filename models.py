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