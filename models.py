class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    care_plan_id = db.Column(db.Integer, db.ForeignKey('care_plan.id'), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey('goal.id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Interval, nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='scheduled')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('activities', lazy=True))
    care_plan = db.relationship('CarePlan', backref=db.backref('activities', lazy=True))
    goal = db.relationship('Goal', backref=db.backref('activities', lazy=True))

    def __repr__(self):
        return f'<Activity {self.title} for Patient {self.patient_id}>' 