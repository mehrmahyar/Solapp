from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, DateField, FloatField, IntegerField, FileField, SelectMultipleField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, NumberRange, URL
from flask_wtf.file import FileAllowed
from models import Team, Exercise, TestTypeEnum, WorkoutCategoryEnum, MoodEnum # Import necessary models/enums
from datetime import date

# Utility function to get choices from Enum
def enum_choices(enum_class):
    return [(choice.name, choice.value) for choice in enum_class]

def get_team_choices():
    # Wrap in try-except in case DB isn't ready during initial load
    try:
        teams = Team.query.order_by(Team.name).all()
        return [(team.id, team.name) for team in teams]
    except Exception:
        return []

def get_exercise_choices():
    try:
        exercises = Exercise.query.order_by(Exercise.name).all()
        return [(ex.id, ex.name) for ex in exercises]
    except Exception:
        return []

# Custom coerce function to handle empty strings for integer SelectFields
def coerce_int_or_none(x):
    if x is None or x == '':
        return None
    try:
        return int(x)
    except (ValueError, TypeError):
        return None # Or raise validation error?

class TeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired(), Length(min=2, max=100)])
    submit = SubmitField('Save Team')

class ClientForm(FlaskForm):
    name = StringField('Player Name', validators=[DataRequired(), Length(min=2, max=100)])
    team_id = SelectField('Team (Optional)', coerce=coerce_int_or_none, validators=[Optional()])
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    position = StringField('Position', validators=[Optional(), Length(max=50)])
    registration_details = TextAreaField('Registration Details', validators=[Optional()])
    # payment_receipt = FileField('Payment Receipt (Optional)') # Add if needed
    approval_status = BooleanField('Approved', default=True)
    submit = SubmitField('Save Player')

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)
        self.team_id.choices = [('', '- No Team -')] + get_team_choices()

from config import Config # Import Config to access questions

# Dynamically created Health Questionnaire Form
class HealthQuestionnaireForm(FlaskForm):
    submit = SubmitField('Save Questionnaire')

    def __init__(self, *args, **kwargs):
        super(HealthQuestionnaireForm, self).__init__(*args, **kwargs)
        # Dynamically add fields based on questions in Config
        for question in Config.HEALTH_QUESTIONNAIRE_QUESTIONS:
            field_id = f"q_{question['id']}"
            field_label = question['label']
            field_type = question['type']
            field_validators = [Optional()] # Default to optional, can be customized later

            # Add DataRequired for boolean 'consent_participation' for example
            if question['id'] == 'consent_participation':
                 field_validators = [DataRequired(message="Consent is required.")]


            if field_type == 'text':
                field = StringField(field_label, validators=field_validators)
            elif field_type == 'textarea':
                field = TextAreaField(field_label, validators=field_validators, render_kw={"rows": 3})
            elif field_type == 'select':
                field = SelectField(field_label, choices=question.get('choices', []), validators=field_validators)
            elif field_type == 'boolean':
                # BooleanField doesn't render label correctly by default with _formhelpers if label text is passed here
                # The label is usually taken from the field name or explicitly in the template.
                # We will handle labels in the template.
                field = BooleanField(field_label, validators=field_validators)
            else:
                continue # Skip unknown field types

            setattr(self, field_id, field)

class ProgressPhotoForm(FlaskForm):
    photo = FileField('Upload Photo', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')
    ])
    upload_date = DateField('Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    angle = SelectField('Angle', choices=[
        ('', '- Select Angle -'),
        ('Front', 'Front'),
        ('Back', 'Back'),
        ('Left', 'Left Side'),
        ('Right', 'Right Side')
        ], validators=[Optional()])
    submit = SubmitField('Upload Photo')

class BodyCompositionForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    weight = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=0)])
    height = FloatField('Height (cm)', validators=[Optional(), NumberRange(min=0)])
    body_fat = FloatField('Body Fat (%)', validators=[Optional(), NumberRange(min=0, max=100)])
    muscle_mass = FloatField('Muscle Mass (kg)', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Save Body Composition')

class PhysicalTestForm(FlaskForm):
    test_type = SelectField('Test Type', choices=enum_choices(TestTypeEnum), validators=[DataRequired()])
    date = DateField('Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    value = StringField('Result/Value', validators=[DataRequired(), Length(max=50)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Test Result')

class BaselineForm(FlaskForm):
    test_type = SelectField('Test Type', choices=enum_choices(TestTypeEnum), validators=[DataRequired()])
    value = StringField('Baseline Value', validators=[DataRequired(), Length(max=50)])
    date_set = DateField('Date Set', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    submit = SubmitField('Set Baseline')

class ExerciseForm(FlaskForm):
    name = StringField('Exercise Name', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Description', validators=[Optional()])
    video_url = StringField('Video URL', validators=[Optional(), URL(), Length(max=255)])
    submit = SubmitField('Save Exercise')

# Form for creating/editing workout programs - Now uses dynamic JS builder
class WorkoutProgramForm(FlaskForm):
    name = StringField('Program Name', validators=[DataRequired(), Length(max=150)])
    date = DateField('Intended Date', format='%Y-%m-%d', validators=[DataRequired()])
    assign_to_team = SelectField('Assign to Team (Optional)', coerce=coerce_int_or_none, validators=[Optional()])
    assign_to_client = SelectField('Assign to Player (Optional)', coerce=coerce_int_or_none, validators=[Optional()])
    notes = TextAreaField('Program Notes', validators=[Optional()])
    # Hidden field to store the JSON data generated by JavaScript
    exercises_json_data = HiddenField('Exercises JSON Data', validators=[Optional()])
    submit = SubmitField('Save Workout Program')

    def __init__(self, *args, **kwargs):
        super(WorkoutProgramForm, self).__init__(*args, **kwargs)
        # Populate team choices
        team_choices = [('', '- Select Team -')] + get_team_choices()
        self.assign_to_team.choices = team_choices
        # Populate client choices
        try:
            from models import Client # Local import to avoid circular dependency if needed
            client_choices = [('', '- Select Player -')] + [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
            self.assign_to_client.choices = client_choices
        except Exception:
             self.assign_to_client.choices = [('', '- Select Player -')] # Handle DB not ready


# Form for logging a training session - Simplified
class TrainingSessionForm(FlaskForm):
    date = DateField('Session Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    workout_program_id = SelectField('Based on Program (Optional)', coerce=coerce_int_or_none, validators=[Optional()])
    duration_minutes = IntegerField('Duration (minutes)', validators=[Optional(), NumberRange(min=0)])
    session_rpe = IntegerField('Session RPE (1-10)', validators=[Optional(), NumberRange(min=1, max=10)])
    session_rating = IntegerField('Session Rating (1-5)', validators=[Optional(), NumberRange(min=1, max=5)])
    # Hidden field to store the JSON data generated by JavaScript for session logs
    session_logs_json_data = HiddenField('Session Logs JSON Data', validators=[Optional()])
    submit = SubmitField('Log Training Session')

    def __init__(self, client_id=None, *args, **kwargs):
        super(TrainingSessionForm, self).__init__(*args, **kwargs)
        # Populate program choices relevant to the client or their team
        program_choices = [('', '- Select Program -')]
        if client_id:
            try:
                from models import Client, WorkoutProgram # Local import
                client = Client.query.get(client_id)
                if client:
                    # Programs assigned directly to client or their team
                    programs = WorkoutProgram.query.filter(
                        (WorkoutProgram.client_id == client_id) | (WorkoutProgram.team_id == client.team_id)
                    ).order_by(WorkoutProgram.date.desc()).limit(20).all() # Limit choices
                    program_choices.extend([(p.id, f"{p.date.strftime('%Y-%m-%d')} - {p.name}") for p in programs])
            except Exception:
                pass # Fail silently if DB not ready
        self.workout_program_id.choices = program_choices


class ReadinessForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    sleep_quality = SelectField('Sleep Quality', coerce=int, choices=[(i, i) for i in range(1, 6)], validators=[Optional()])
    sleep_duration = FloatField('Sleep Duration (hours)', validators=[Optional(), NumberRange(min=0, max=24)])
    muscle_soreness = SelectField('Muscle Soreness (5=Best)', coerce=int, choices=[(i, i) for i in range(1, 6)], validators=[Optional()])
    fatigue_level = SelectField('Fatigue Level (5=Best)', coerce=int, choices=[(i, i) for i in range(1, 6)], validators=[Optional()])
    mood = SelectField('Mood (5=Best)', coerce=int, choices=[(i, i) for i in range(1, 6)], validators=[Optional()])
    stress_level = SelectField('Stress Level (5=Best)', coerce=int, choices=[(i, i) for i in range(1, 6)], validators=[Optional()])
    confidence = SelectField('Training Confidence (5=Best)', coerce=int, choices=[(i, i) for i in range(1, 6)], validators=[Optional()])
    injury_pain = BooleanField('Any Injury/Pain?')
    comments = TextAreaField('Comments', validators=[Optional()])
    cmj_result = FloatField('CMJ Result (cm - Optional)', validators=[Optional(), NumberRange(min=0)])
    drop_jump_result = FloatField('Drop Jump Result (RSI - Optional)', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Save Readiness')

class ReportForm(FlaskForm):
    report_type = SelectField('Report For', choices=[('client', 'Individual Player'), ('team', 'Team')], validators=[DataRequired()])
    client_id = SelectField('Select Player', coerce=coerce_int_or_none, validators=[Optional()])
    team_id = SelectField('Select Team', coerce=coerce_int_or_none, validators=[Optional()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', default=date.today, validators=[DataRequired()])
    submit = SubmitField('Generate Report')

    def __init__(self, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        self.team_id.choices = [('', '- Select Team -')] + get_team_choices()
        # Client choices
        try:
            from models import Client
            self.client_id.choices = [('', '- Select Player -')] + [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
        except Exception:
            self.client_id.choices = [('', '- Select Player -')] 