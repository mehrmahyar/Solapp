from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import enum
import json

db = SQLAlchemy()

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    players = db.relationship('Client', backref='team', lazy=True)

    def __repr__(self):
        return f'<Team {self.name}>'

class Client(db.Model):
    __tablename__ = 'clients' # Match schema name
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True) # Allow clients without a team
    registration_details = db.Column(db.Text, nullable=True) # General details
    payment_receipt_path = db.Column(db.String(255), nullable=True) # If needed
    approval_status = db.Column(db.Boolean, default=True) # Assuming default approved
    dob = db.Column(db.Date, nullable=True) # Added from CHATGPT solution
    position = db.Column(db.String(50), nullable=True) # Added from CHATGPT solution

    # Relationships
    health_questionnaires = db.relationship('HealthQuestionnaire', backref='client', lazy=True, uselist=False) # One-to-one assuming latest
    progress_photos = db.relationship('ProgressPhoto', backref='client', lazy=True, order_by="desc(ProgressPhoto.upload_date)")
    body_compositions = db.relationship('BodyComposition', backref='client', lazy=True, order_by="desc(BodyComposition.date)")
    physical_tests = db.relationship('PhysicalTest', backref='client', lazy=True, order_by="desc(PhysicalTest.date)")
    workout_programs = db.relationship('WorkoutProgram', backref='client', lazy=True, order_by="desc(WorkoutProgram.date)")
    training_sessions = db.relationship('TrainingSession', backref='client', lazy=True, order_by="desc(TrainingSession.date)")
    readiness_entries = db.relationship('Readiness', backref='client', lazy=True, order_by="desc(Readiness.date)")
    baselines = db.relationship('Baseline', backref='client', lazy=True)

    # Indexes for common lookups
    __table_args__ = (db.Index('ix_clients_name', 'name'),
                      db.Index('ix_clients_team_id', 'team_id'))

    def __repr__(self):
        return f'<Client {self.name}>'

class HealthQuestionnaire(db.Model):
    __tablename__ = 'health_questionnaires'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, unique=True)
    responses = db.Column(db.JSON, nullable=True) # Store questions and answers
    submission_date = db.Column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (db.Index('ix_health_questionnaires_client_id_date', 'client_id', 'submission_date'),)

class ProgressPhoto(db.Model):
    __tablename__ = 'progress_photos'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    upload_date = db.Column(db.Date, nullable=False, default=func.current_date())
    photo_path = db.Column(db.String(255), nullable=False) # Path relative to UPLOAD_FOLDER
    angle = db.Column(db.String(50), nullable=True) # e.g., Front, Back, Left, Right

    __table_args__ = (db.Index('ix_progress_photos_client_id_date', 'client_id', 'upload_date'),)

class BodyComposition(db.Model):
    __tablename__ = 'body_composition'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=func.current_date())
    weight = db.Column(db.Float, nullable=True)
    body_fat = db.Column(db.Float, nullable=True) # Percentage
    muscle_mass = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True) # Added from CHATGPT suggestion

    __table_args__ = (db.Index('ix_body_composition_client_id_date', 'client_id', 'date'),)

# Enum for standard test types - Can be expanded
class TestTypeEnum(enum.Enum):
    CMJ = "CMJ"
    DROP_JUMP = "Drop Jump"
    ARM_SWING_CMJ = "Arm Swing CMJ"
    YO_YO_IR1 = "Yo-Yo IR1"
    SPRINT_20YD = "20yd Sprint"
    FMS = "FMS"
    VERTICAL_JUMP = "Vertical Jump"
    SQUAT_PATTERN = "Squat Pattern"
    STRENGTH_ENDURANCE = "Strength Endurance"
    OTHER = "Other"

class PhysicalTest(db.Model):
    __tablename__ = 'physical_tests'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    # test_type = db.Column(db.String(100), nullable=False)
    test_type = db.Column(db.Enum(TestTypeEnum), nullable=False)
    date = db.Column(db.Date, nullable=False, default=func.current_date())
    value = db.Column(db.String(50), nullable=False) # String to accommodate scores like "Level 16.3" or "18/21"
    notes = db.Column(db.Text, nullable=True)

    __table_args__ = (db.Index('ix_physical_tests_client_id_date', 'client_id', 'date'),
                      db.Index('ix_physical_tests_client_id_type', 'client_id', 'test_type'))

class Baseline(db.Model):
    __tablename__ = 'baselines'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    # test_type = db.Column(db.String(100), nullable=False)
    test_type = db.Column(db.Enum(TestTypeEnum), nullable=False)
    value = db.Column(db.String(50), nullable=False)
    date_set = db.Column(db.Date, nullable=False, default=func.current_date())
    # Remove misplaced column and incorrect index definitions from here

    # Ensure one baseline per test type per client - UniqueConstraint implies an index
    __table_args__ = (db.UniqueConstraint('client_id', 'test_type', name='uq_client_test_baseline'),)

class Exercise(db.Model):
    __tablename__ = 'exercises'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(255), nullable=True)

# Enum for Workout Categories
class WorkoutCategoryEnum(enum.Enum):
    WARM_UP = "Warm-Up"
    CORE = "Core"
    COOL_DOWN = "Cool-Down"
    ENDURANCE = "Endurance"
    ACCESSORY = "Accessory"
    OTHER = "Other"

class WorkoutProgram(db.Model):
    __tablename__ = 'workout_programs'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True) # Can be assigned later
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True) # Assign to team
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False) # Date the program is intended for
    notes = db.Column(db.Text, nullable=True)
    # Store exercise details as JSON for simplicity in this local app context
    # Structure: { "exercises": [{"exercise_id": 1, "sets": 3, "reps": "8-10", "rest": "60s", "category": "Core", "notes": "Focus on form"}, ...]}
    exercises_json = db.Column(db.JSON, nullable=True)

    __table_args__ = (db.Index('ix_workout_programs_client_id_date', 'client_id', 'date'),
                      db.Index('ix_workout_programs_team_id_date', 'team_id', 'date'))

    # Ensure either client_id or team_id is set, or maybe program is just a template?
    # Add check constraint or handle in application logic

class TrainingSession(db.Model):
    __tablename__ = 'training_sessions'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=func.current_date())
    workout_program_id = db.Column(db.Integer, db.ForeignKey('workout_programs.id'), nullable=True) # Link to the planned program
    # Store logs as JSON: { "session_rpe": 8, "session_rating": 4, "logs": [{"exercise_id": 1, "set": 1, "weight": 100, "reps": 8, "velocity": "0.5", "set_rpe": 7, "notes": "Felt good"}, ...]}
    logs = db.Column(db.JSON, nullable=True)
    session_rpe = db.Column(db.Integer, nullable=True) # Overall session RPE (1-10)
    session_rating = db.Column(db.Integer, nullable=True) # Overall session rating (e.g., 1-5 stars)
    duration_minutes = db.Column(db.Integer, nullable=True)

    __table_args__ = (db.Index('ix_training_sessions_client_id_date', 'client_id', 'date'),
                      db.Index('ix_training_sessions_program_id', 'workout_program_id'))

# Enum for Mood - Simplified
class MoodEnum(enum.Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"

class Readiness(db.Model):
    __tablename__ = 'readiness'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=func.current_date())

    # Subjective Measures (Using 1-5 scale from alternative method for simplicity)
    sleep_quality = db.Column(db.Integer, nullable=True) # 1-5
    sleep_duration = db.Column(db.Float, nullable=True) # Hours
    muscle_soreness = db.Column(db.Integer, nullable=True) # 1-5 (5=Excellent/No soreness)
    fatigue_level = db.Column(db.Integer, nullable=True) # 1-5 (5=Excellent/No fatigue)
    mood = db.Column(db.Integer, nullable=True) # 1-5
    stress_level = db.Column(db.Integer, nullable=True) # 1-5 (5=Excellent/No stress)
    confidence = db.Column(db.Integer, nullable=True) # 1-5
    injury_pain = db.Column(db.Boolean, default=False) # Yes/No
    comments = db.Column(db.Text, nullable=True)

    # Objective Measures (Optional)
    cmj_result = db.Column(db.Float, nullable=True)
    drop_jump_result = db.Column(db.Float, nullable=True)

    # Calculated Score (Optional - could be calculated on the fly)
    calculated_readiness_score = db.Column(db.Float, nullable=True)

    # Ensure one entry per client per day - This unique constraint implies an index
    __table_args__ = (db.UniqueConstraint('client_id', 'date', name='uq_client_readiness_date'),)

# Helper to get baseline value safely (returns None if not found)
def get_baseline_value(client_id, test_type_enum):
    baseline = Baseline.query.filter_by(client_id=client_id, test_type=test_type_enum).first()
    if baseline and baseline.value:
        try:
            # Attempt to convert to float, handle cases like "18/21" or levels gracefully
            # More robust parsing might be needed depending on exact formats used
            if '/' in baseline.value:
                # Handle ratio like FMS score
                parts = baseline.value.split('/')
                return float(parts[0]) # Return the score part
            elif 'Level' in baseline.value:
                 # Handle YoYo test levels
                 return float(baseline.value.split(' ')[-1])
            else:
                return float(baseline.value)
        except (ValueError, TypeError):
            return None # Cannot parse as a number relevant for ratio calc
    return None 