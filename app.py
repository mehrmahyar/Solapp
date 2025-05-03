import os
import json

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func # Import func for avg calculation
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import date, timedelta
import logging # Added for logging

from config import Config
from models import (db, Team, Client, HealthQuestionnaire, ProgressPhoto, BodyComposition,
                    PhysicalTest, Baseline, Exercise, WorkoutProgram, TrainingSession,
                    Readiness, TestTypeEnum, WorkoutCategoryEnum)
from forms import (TeamForm, ClientForm, HealthQuestionnaireForm, ProgressPhotoForm, BodyCompositionForm,
                   PhysicalTestForm, BaselineForm, ExerciseForm, WorkoutProgramForm, TrainingSessionForm,
                   ReadinessForm, ReportForm)
from utils import (calculate_readiness_score, generate_report_pdf, get_report_data,
                   create_readiness_plot, create_body_composition_plot, create_physical_test_plot)
import plotly.io as pio

# Initialize App
app = Flask(__name__)
app.config.from_object(Config)

# Enable Jinja extensions (like `do`)
app.jinja_env.add_extension('jinja2.ext.do')

# Configure Logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Initialize Extensions
db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    app.logger.info(f"Created upload directory: {app.config['UPLOAD_FOLDER']}")

# Create database tables if they don't exist (simple setup for local app)
with app.app_context():
    try:
        # db.create_all() # Handled by migrations now
        app.logger.info("Database tables should be managed via Flask-Migrate.")
    except Exception as e:
        app.logger.error(f"Error during initial app context setup: {e}")

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

# --- Routes ---

@app.route('/')
def index():
    try:
        teams_count = Team.query.count()
        clients_count = Client.query.count()
        # Basic dashboard stats - enhance later
        today_readiness_avg = db.session.query(func.avg(Readiness.calculated_readiness_score)) \
                                       .filter(Readiness.date == date.today()).scalar()
        today_readiness_count = Readiness.query.filter(Readiness.date == date.today()).count()

    except Exception as e:
        app.logger.error(f"Error fetching dashboard data: {e}")
        flash('Error loading dashboard data.', 'danger')
        teams_count = 0
        clients_count = 0
        today_readiness_avg = None
        today_readiness_count = 0

    return render_template('index.html', teams_count=teams_count, clients_count=clients_count,
                           today_readiness_avg=today_readiness_avg,
                           today_readiness_count=today_readiness_count)

# -- Team Management --
@app.route('/teams')
def list_teams():
    try:
        page = request.args.get('page', 1, type=int)
        teams_query = Team.query.order_by(Team.name)
        pagination = teams_query.paginate(page=page, per_page=15, error_out=False)
        teams = pagination.items
    except Exception as e:
        app.logger.error(f"Error fetching teams: {e}")
        flash('Error loading teams.', 'danger')
        teams = []
        pagination = None
    return render_template('teams/list.html', teams=teams, pagination=pagination)

@app.route('/teams/add', methods=['GET', 'POST'])
def add_team():
    form = TeamForm()
    if form.validate_on_submit():
        team = Team(name=form.name.data)
        db.session.add(team)
        try:
            db.session.commit()
            flash(f'Team "{team.name}" added successfully!', 'success')
            return redirect(url_for('list_teams'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding team: {e}")
            flash(f'Error adding team: {e}', 'danger')
    return render_template('teams/add_edit.html', form=form, title="Add New Team")

@app.route('/teams/edit/<int:team_id>', methods=['GET', 'POST'])
def edit_team(team_id):
    team = Team.query.get_or_404(team_id)
    form = TeamForm(obj=team)
    if form.validate_on_submit():
        team.name = form.name.data
        try:
            db.session.commit()
            flash(f'Team "{team.name}" updated successfully!', 'success')
            return redirect(url_for('list_teams'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating team {team_id}: {e}")
            flash(f'Error updating team: {e}', 'danger')
    return render_template('teams/add_edit.html', form=form, title="Edit Team", team=team)

@app.route('/teams/delete/<int:team_id>', methods=['POST'])
def delete_team(team_id):
    team = Team.query.get_or_404(team_id)
    if team.players: # Prevent deletion if team has players
        flash('Cannot delete team with players assigned. Please reassign players first.', 'warning')
        return redirect(url_for('list_teams'))
    try:
        db.session.delete(team)
        db.session.commit()
        flash(f'Team "{team.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting team {team_id}: {e}")
        flash(f'Error deleting team: {e}', 'danger')
    return redirect(url_for('list_teams'))

# -- Player/Client Management --
@app.route('/clients')
def list_clients():
    try:
        page = request.args.get('page', 1, type=int)
        # Use outerjoin to include clients without teams, order by team name (None first), then client name
        clients_query = Client.query.outerjoin(Team).order_by(Team.name.nullsfirst(), Client.name)
        pagination = clients_query.paginate(page=page, per_page=15, error_out=False) # Configurable per_page
        clients = pagination.items
    except Exception as e:
        app.logger.error(f"Error fetching clients: {e}")
        flash('Error loading players list.', 'danger')
        clients = []
        pagination = None # Ensure pagination is None on error
    # TODO: Add filter parameter (e.g., ?filter=individual) and logic here
    # TODO: Update clients/list.html to handle and display team optionality / filters
    return render_template('clients/list.html', clients=clients, pagination=pagination)

@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            name=form.name.data,
            # team_id will be None if 'No Team' was selected, thanks to coerce_int_or_none
            team_id=form.team_id.data,
            dob=form.dob.data,
            position=form.position.data,
            registration_details=form.registration_details.data,
            approval_status=form.approval_status.data
        )
        db.session.add(client)
        try:
            db.session.commit()
            flash(f'Player "{client.name}" added successfully!', 'success')
            return redirect(url_for('view_client', client_id=client.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding client: {e}")
            flash(f'Error adding player: {e}', 'danger')
    # elif request.method == 'GET' and not Team.query.first(): # Check if teams exist on GET
    #      # This check is no longer needed as individual clients are allowed
    #      flash('Please add a team first before adding players.', 'warning')
    #      return redirect(url_for('add_team'))
    return render_template('clients/add_edit.html', form=form, title="Add New Player")


@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        client.name = form.name.data
        client.team_id = form.team_id.data
        client.dob = form.dob.data
        client.position = form.position.data
        client.registration_details = form.registration_details.data
        client.approval_status = form.approval_status.data
        try:
            db.session.commit()
            flash(f'Player "{client.name}" updated successfully!', 'success')
            return redirect(url_for('view_client', client_id=client.id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating client {client_id}: {e}")
            flash(f'Error updating player: {e}', 'danger')
    return render_template('clients/add_edit.html', form=form, title="Edit Player", client=client)

@app.route('/clients/view/<int:client_id>')
def view_client(client_id):
    client = Client.query.get_or_404(client_id)
    # Fetch related data for tabs
    today = date.today()
    # Default range for plots (e.g., last 30 days)
    start_date_default = today - timedelta(days=30)

    # Generate plots for display
    readiness_plot_html = None
    body_comp_plot_html = None
    test_plots_html = {}

    try:
        readiness_fig = create_readiness_plot(client_id, start_date_default, today)
        if readiness_fig:
            readiness_plot_html = pio.to_html(readiness_fig, full_html=False, include_plotlyjs='cdn')

        body_comp_fig = create_body_composition_plot(client_id, start_date_default, today)
        if body_comp_fig:
            body_comp_plot_html = pio.to_html(body_comp_fig, full_html=False, include_plotlyjs='cdn')

        # Add plots for key physical tests
        key_tests = [TestTypeEnum.CMJ, TestTypeEnum.DROP_JUMP, TestTypeEnum.SPRINT_20YD]
        for test_type in key_tests:
            test_fig = create_physical_test_plot(client_id, test_type, start_date_default, today)
            if test_fig:
                test_plots_html[test_type.value] = pio.to_html(test_fig, full_html=False, include_plotlyjs='cdn')

    except Exception as e:
         app.logger.error(f"Error generating plots for client {client_id}: {e}")
         flash("Error generating some plots for the profile view.", "warning")

    # Fetch workout for today to display
    today_program = WorkoutProgram.query.filter(
                        (WorkoutProgram.client_id == client_id) | (WorkoutProgram.team_id == client.team_id),
                        WorkoutProgram.date == today
                    ).first()
    program_exercises = None
    if today_program and today_program.exercises_json:
        try:
            # Enrich exercise details with names from Exercise table
            exercise_data = today_program.exercises_json.get('exercises', [])
            exercise_ids = [item.get('exercise_id') for item in exercise_data if item.get('exercise_id')]
            exercises_db = {ex.id: ex for ex in Exercise.query.filter(Exercise.id.in_(exercise_ids)).all()}
            for item in exercise_data:
                exercise_id = item.get('exercise_id')
                exercise_obj = exercises_db.get(exercise_id)
                item['name'] = exercise_obj.name if exercise_obj else 'Unknown Exercise'
                item['video_url'] = exercise_obj.video_url if exercise_obj else None

            # Group by category
            program_exercises = {}
            categories = [cat.value for cat in WorkoutCategoryEnum]
            for cat in categories:
                program_exercises[cat] = [ex for ex in exercise_data if ex.get('category') == cat]

        except Exception as e:
            app.logger.error(f"Error processing today's workout program JSON for client {client_id}: {e}")
            program_exercises = None # Fail gracefully

    # Fetch other data for tabs
    health_questionnaire = HealthQuestionnaire.query.filter_by(client_id=client_id).first()
    progress_photos = ProgressPhoto.query.filter_by(client_id=client_id).order_by(ProgressPhoto.upload_date.desc()).all()
    body_comps = BodyComposition.query.filter_by(client_id=client_id).order_by(BodyComposition.date.desc()).limit(10).all() # Example: Limit last 10
    physical_tests = PhysicalTest.query.filter_by(client_id=client_id).order_by(PhysicalTest.date.desc(), PhysicalTest.test_type).limit(20).all() # Example: Limit last 20
    baselines = Baseline.query.filter_by(client_id=client_id).order_by(Baseline.test_type).all()
    training_sessions = TrainingSession.query.filter_by(client_id=client_id).order_by(TrainingSession.date.desc()).limit(10).all() # Example: Limit last 10
    readiness_entries = Readiness.query.filter_by(client_id=client_id).order_by(Readiness.date.desc()).limit(10).all() # Example: Limit last 10

    return render_template('clients/view.html', client=client,
                           readiness_plot_html=readiness_plot_html,
                           body_comp_plot_html=body_comp_plot_html,
                           test_plots_html=test_plots_html,
                           today_program=today_program,
                           program_exercises=program_exercises,
                           health_questionnaire=health_questionnaire,
                           progress_photos=progress_photos,
                           body_comps=body_comps,
                           physical_tests=physical_tests,
                           baselines=baselines,
                           training_sessions=training_sessions,
                           readiness_entries=readiness_entries)


@app.route('/clients/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    client_name = client.name
    # Consider implications: delete related data? Or just mark as inactive?
    # Simple deletion for now, including photos:
    app.logger.info(f"Attempting to delete client {client_id} ('{client_name}') and associated data.")
    try:
        # Delete associated photos from filesystem first
        photos_to_delete = ProgressPhoto.query.filter_by(client_id=client_id).all()
        for photo in photos_to_delete:
            try:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo.photo_path)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    app.logger.info(f"Deleted photo file: {filepath}")
            except Exception as e:
                app.logger.error(f"Error deleting photo file {photo.photo_path}: {e}")

        # Manually delete related data first using bulk deletes (cascade might be better long-term)
        HealthQuestionnaire.query.filter_by(client_id=client_id).delete()
        ProgressPhoto.query.filter_by(client_id=client_id).delete()
        BodyComposition.query.filter_by(client_id=client_id).delete()
        PhysicalTest.query.filter_by(client_id=client_id).delete()
        Baseline.query.filter_by(client_id=client_id).delete()
        # WorkoutProgram assignment - if client specific, delete here too
        WorkoutProgram.query.filter_by(client_id=client_id).delete()
        TrainingSession.query.filter_by(client_id=client_id).delete()
        Readiness.query.filter_by(client_id=client_id).delete()

        # Finally, delete the client record
        db.session.delete(client)
        db.session.commit()
        flash(f'Player "{client_name}" and associated data deleted successfully!', 'success')
        app.logger.info(f"Successfully deleted client {client_id} ('{client_name}').")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting player {client_id}: {e}")
        flash(f'Error deleting player: {e}', 'danger')
    return redirect(url_for('list_clients'))

# --- Data Entry Routes (per client) ---

@app.route('/clients/<int:client_id>/add_health_questionnaire', methods=['GET', 'POST'])
def add_health_questionnaire(client_id):
    client = Client.query.get_or_404(client_id)
    existing_hq = HealthQuestionnaire.query.filter_by(client_id=client_id).first()
    form = HealthQuestionnaireForm()

    if existing_hq and request.method == 'GET':
        try:
            responses_dict = existing_hq.responses or {}
            # Keep simple text format for now
            form.responses_text.data = "\n".join([f"{k}={v}" for k, v in responses_dict.items()])
        except Exception as e:
            app.logger.warning(f"Could not prefill questionnaire for client {client_id}: {e}")
            form.responses_text.data = str(existing_hq.responses) # Fallback

    if form.validate_on_submit():
        # Basic parsing from text area - needs robust implementation
        responses_dict = {}
        for line in form.responses_text.data.strip().split('\n'):
            if '=' in line:
                try:
                    key, value = line.split('=', 1)
                    responses_dict[key.strip()] = value.strip()
                except ValueError:
                     app.logger.warning(f"Skipping invalid line in questionnaire input: {line}")
                     continue # Skip malformed lines

        if not responses_dict:
             flash('No valid questionnaire data entered (use format: Question=Answer).', 'warning')
        else:
            if existing_hq:
                existing_hq.responses = responses_dict
                action = "updated"
            else:
                hq = HealthQuestionnaire(client_id=client_id, responses=responses_dict)
                db.session.add(hq)
                action = "saved"
            try:
                db.session.commit()
                flash(f'Health Questionnaire {action}.', 'success')
                return redirect(url_for('view_client', client_id=client_id, _anchor='health'))
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving questionnaire for client {client_id}: {e}")
                flash(f'Error saving questionnaire: {e}', 'danger')

    title = "Edit Health Questionnaire" if existing_hq else "Add Health Questionnaire"
    return render_template('data_entry/generic_form.html', form=form, title=title, client=client,
                           instructions="Enter health details using the format 'Question=Answer' on each line.")


@app.route('/clients/<int:client_id>/add_progress_photo', methods=['GET', 'POST'])
def add_progress_photo(client_id):
    client = Client.query.get_or_404(client_id)
    form = ProgressPhotoForm()
    if form.validate_on_submit():
        file = form.photo.data
        if file and allowed_file(file.filename):
            # Create a more unique filename
            timestamp = date.today().strftime('%Y%m%d')
            random_hex = os.urandom(4).hex()
            original_filename = secure_filename(file.filename)
            # Sanitize angle for filename
            safe_angle = secure_filename(form.angle.data or 'photo')
            filename = f"{client_id}_{timestamp}_{safe_angle}_{random_hex}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                # Consider image resizing/compression here using Pillow
                file.save(filepath)
                app.logger.info(f"Saved photo file: {filepath}")
                photo = ProgressPhoto(
                    client_id=client_id,
                    upload_date=form.upload_date.data,
                    photo_path=filename, # Store relative path
                    angle=form.angle.data
                )
                db.session.add(photo)
                db.session.commit()
                flash('Progress photo uploaded successfully!', 'success')
                return redirect(url_for('view_client', client_id=client_id, _anchor='photos')) # Go to photos tab
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error saving photo record for client {client_id}: {e}")
                flash(f'Error saving photo record: {e}', 'danger')
                # Clean up saved file if DB commit failed
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        app.logger.info(f"Cleaned up photo file after DB error: {filepath}")
                    except Exception as remove_e:
                        app.logger.error(f"Error cleaning up photo file {filepath}: {remove_e}")
        else:
            flash('Invalid file type or no file selected.', 'warning')
    return render_template('data_entry/generic_form.html', form=form, title="Upload Progress Photo", client=client)

# Route to serve uploaded files
@app.route('/uploads/<path:filename>') # Use path converter for potential subdirs
def uploaded_file(filename):
    # Basic security check - avoid directory traversal
    if '..' in filename or filename.startswith('/'):
        abort(404)
    try:
        # Ensure the UPLOAD_FOLDER exists and is configured
        upload_dir = app.config.get('UPLOAD_FOLDER')
        if not upload_dir or not os.path.isdir(upload_dir):
            app.logger.error(f"UPLOAD_FOLDER '{upload_dir}' is not configured or does not exist.")
            abort(500) # Internal server error
        return send_from_directory(upload_dir, filename, as_attachment=False) # Serve inline
    except FileNotFoundError:
        app.logger.warning(f"Upload file not found: {filename}")
        abort(404)


@app.route('/clients/<int:client_id>/add_body_composition', methods=['GET', 'POST'])
def add_body_composition(client_id):
    client = Client.query.get_or_404(client_id)
    form = BodyCompositionForm()
    if form.validate_on_submit():
        entry = BodyComposition(
            client_id=client_id,
            date=form.date.data,
            weight=form.weight.data,
            height=form.height.data,
            body_fat=form.body_fat.data,
            muscle_mass=form.muscle_mass.data
        )
        db.session.add(entry)
        try:
            db.session.commit()
            flash('Body Composition data saved.', 'success')
            return redirect(url_for('view_client', client_id=client_id, _anchor='bodycomp'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving body comp for client {client_id}: {e}")
            flash(f'Error saving Body Composition: {e}', 'danger')
    return render_template('data_entry/generic_form.html', form=form, title="Add Body Composition Entry", client=client)

@app.route('/clients/<int:client_id>/add_physical_test', methods=['GET', 'POST'])
def add_physical_test(client_id):
    client = Client.query.get_or_404(client_id)
    form = PhysicalTestForm()
    if form.validate_on_submit():
        try:
            test_type_enum = TestTypeEnum[form.test_type.data] # Get enum member from string
        except KeyError:
             flash(f"Invalid test type selected: {form.test_type.data}", 'danger')
             return render_template('data_entry/generic_form.html', form=form, title="Add Physical Test Result", client=client)

        entry = PhysicalTest(
            client_id=client_id,
            test_type=test_type_enum,
            date=form.date.data,
            value=form.value.data,
            notes=form.notes.data
        )
        db.session.add(entry)
        try:
            db.session.commit()
            flash(f'{test_type_enum.value} test result saved.', 'success')
            return redirect(url_for('view_client', client_id=client_id, _anchor='tests'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving physical test for client {client_id}: {e}")
            flash(f'Error saving test result: {e}', 'danger')
    return render_template('data_entry/generic_form.html', form=form, title="Add Physical Test Result", client=client)

@app.route('/clients/<int:client_id>/add_baseline', methods=['GET', 'POST'])
def add_baseline(client_id):
    client = Client.query.get_or_404(client_id)
    form = BaselineForm()
    if form.validate_on_submit():
        try:
            test_type_enum = TestTypeEnum[form.test_type.data]
        except KeyError:
             flash(f"Invalid test type selected: {form.test_type.data}", 'danger')
             # Redirect back to the form, not just client view
             return redirect(url_for('add_baseline', client_id=client_id))

        # Check if baseline for this test type already exists
        existing_baseline = Baseline.query.filter_by(client_id=client_id, test_type=test_type_enum).first()
        if existing_baseline:
            existing_baseline.value = form.value.data
            existing_baseline.date_set = form.date_set.data
            action = "updated"
            flash(f'{test_type_enum.value} baseline updated.', 'info')
        else:
            baseline = Baseline(
                client_id=client_id,
                test_type=test_type_enum,
                value=form.value.data,
                date_set=form.date_set.data
            )
            db.session.add(baseline)
            action = "set"
            flash(f'{test_type_enum.value} baseline set.', 'success')
        try:
            db.session.commit()
            # Redirect back to the baseline form to see the update
            return redirect(url_for('add_baseline', client_id=client_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error {action} baseline for client {client_id}, test {test_type_enum.name}: {e}")
            flash(f'Error saving baseline: {e}', 'danger')

    # Fetch current baselines to display on the form page
    try:
        baselines = Baseline.query.filter_by(client_id=client_id).order_by(Baseline.test_type).all()
    except Exception as e:
        app.logger.error(f"Error fetching baselines for client {client_id}: {e}")
        flash("Error loading current baselines.", "warning")
        baselines = []

    return render_template('data_entry/baseline_form.html', form=form, title="Set/Update Baselines", client=client, baselines=baselines)


@app.route('/clients/<int:client_id>/add_readiness', methods=['GET', 'POST'])
def add_readiness(client_id):
    client = Client.query.get_or_404(client_id)
    form = ReadinessForm()
    form_title = "Add Daily Readiness"

    if form.validate_on_submit():
        # Check if entry for this date already exists
        existing_entry = Readiness.query.filter_by(client_id=client_id, date=form.date.data).first()
        if existing_entry:
             action = "updated"
             flash(f'Readiness entry for {form.date.data.strftime("%Y-%m-%d")} already exists. Updating it.', 'info')
             entry = existing_entry
        else:
             action = "saved"
             entry = Readiness(client_id=client_id)

        # Populate entry from form
        entry.date = form.date.data
        entry.sleep_quality = form.sleep_quality.data
        entry.sleep_duration = form.sleep_duration.data
        entry.muscle_soreness = form.muscle_soreness.data
        entry.fatigue_level = form.fatigue_level.data
        entry.mood = form.mood.data
        entry.stress_level = form.stress_level.data
        entry.confidence = form.confidence.data
        entry.injury_pain = form.injury_pain.data
        entry.comments = form.comments.data
        entry.cmj_result = form.cmj_result.data
        entry.drop_jump_result = form.drop_jump_result.data

        # Calculate score
        try:
            entry.calculated_readiness_score = calculate_readiness_score(entry)
        except Exception as calc_e:
             app.logger.error(f"Error calculating readiness score for client {client_id}, date {entry.date}: {calc_e}")
             flash("Error calculating readiness score.", "warning")
             entry.calculated_readiness_score = None # Ensure it's null if calc fails

        if action == "saved":
             db.session.add(entry)

        try:
            db.session.commit()
            score_str = f"{entry.calculated_readiness_score:.1f}" if entry.calculated_readiness_score is not None else "N/A"
            flash(f'Readiness data for {entry.date.strftime("%Y-%m-%d")} {action}. Score: {score_str}', 'success')
            return redirect(url_for('view_client', client_id=client_id, _anchor='readiness'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving readiness data for client {client_id}: {e}")
            flash(f'Error saving readiness data: {e}', 'danger')

    elif request.method == 'GET':
        # Try to pre-fill if editing today's entry or specific date from query param?
        edit_date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
        try:
            edit_date = date.fromisoformat(edit_date_str)
            existing_entry = Readiness.query.filter_by(client_id=client_id, date=edit_date).first()
            if existing_entry:
                 form = ReadinessForm(obj=existing_entry)
                 form_title = f"Edit Daily Readiness ({edit_date_str})"
                 flash(f'Editing readiness entry for {edit_date_str}.', 'info')
            else:
                 # Set date field to the target date if adding new
                 form.date.data = edit_date
                 form_title = f"Add Daily Readiness ({edit_date_str})"
        except (ValueError, TypeError):
            app.logger.warning(f"Invalid date format in query param for readiness: {edit_date_str}")
            # Default to today if date param is invalid
            form.date.data = date.today()
            form_title = "Add Daily Readiness (Today)"

    return render_template('data_entry/generic_form.html', form=form, title=form_title, client=client)

# -- Exercise Library --
@app.route('/exercises')
def list_exercises():
    try:
        page = request.args.get('page', 1, type=int)
        exercises_query = Exercise.query.order_by(Exercise.name)
        pagination = exercises_query.paginate(page=page, per_page=15, error_out=False)
        exercises = pagination.items
    except Exception as e:
        app.logger.error(f"Error fetching exercises: {e}")
        flash("Error loading exercise library.", "danger")
        exercises = []
        pagination = None
    return render_template('exercises/list.html', exercises=exercises, pagination=pagination)

@app.route('/exercises/add', methods=['GET', 'POST'])
def add_exercise():
    form = ExerciseForm()
    if form.validate_on_submit():
        exercise = Exercise(
            name=form.name.data,
            description=form.description.data,
            video_url=form.video_url.data
        )
        db.session.add(exercise)
        try:
            db.session.commit()
            flash(f'Exercise "{exercise.name}" added.', 'success')
            return redirect(url_for('list_exercises'))
        except Exception as e:
            db.session.rollback()
            # Handle potential unique constraint violation (name)
            if 'UNIQUE constraint failed' in str(e):
                 flash(f'Error: An exercise with the name "{form.name.data}" already exists.', 'danger')
            else:
                 app.logger.error(f"Error adding exercise: {e}")
                 flash(f'Error adding exercise: {e}', 'danger')
    return render_template('exercises/add_edit.html', form=form, title="Add New Exercise")

@app.route('/exercises/edit/<int:exercise_id>', methods=['GET', 'POST'])
def edit_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    form = ExerciseForm(obj=exercise)
    if form.validate_on_submit():
        exercise.name = form.name.data
        exercise.description = form.description.data
        exercise.video_url = form.video_url.data
        try:
            db.session.commit()
            flash(f'Exercise "{exercise.name}" updated.', 'success')
            return redirect(url_for('list_exercises'))
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e):
                 flash(f'Error: An exercise with the name "{form.name.data}" already exists.', 'danger')
            else:
                 app.logger.error(f"Error updating exercise {exercise_id}: {e}")
                 flash(f'Error updating exercise: {e}', 'danger')
    return render_template('exercises/add_edit.html', form=form, title="Edit Exercise", exercise=exercise)

@app.route('/exercises/delete/<int:exercise_id>', methods=['POST'])
def delete_exercise(exercise_id):
    exercise = Exercise.query.get_or_404(exercise_id)
    exercise_name = exercise.name
    # TODO: Add check: Query WorkoutProgram.exercise_json for exercise_id
    try:
        db.session.delete(exercise)
        db.session.commit()
        flash(f'Exercise "{exercise_name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting exercise {exercise_id}: {e}")
        # Provide more context if deletion fails due to constraints (e.g., foreign key)
        flash(f'Error deleting exercise: {e}. It might be used in existing workout programs.', 'danger')
    return redirect(url_for('list_exercises'))

# -- Workout Programs --
@app.route('/workout_programs')
def list_workout_programs():
    try:
        page = request.args.get('page', 1, type=int)
        # Query programs, joining with Client and Team to get names efficiently
        programs_query = (
            db.session.query(
                WorkoutProgram,
                Client.name.label('client_name'),
                Team.name.label('team_name')
            ).outerjoin(Client, WorkoutProgram.client_id == Client.id)
            .outerjoin(Team, WorkoutProgram.team_id == Team.id)
            .order_by(WorkoutProgram.date.desc())
        )

        pagination = programs_query.paginate(page=page, per_page=10, error_out=False)
        programs_data = pagination.items # List of tuples (WorkoutProgram, client_name, team_name)

        # Pass the pagination object and the queried data to the template
        return render_template('programs/list.html', pagination=pagination, programs_data=programs_data)
    except Exception as e:
        app.logger.error(f"Error fetching workout programs: {e}")
        flash(f'Error loading workout programs: {e}', 'danger')
        # Redirect to index or return a simple error page in case of failure
        return render_template('programs/list.html', pagination=None, programs_data=[])


@app.route('/workout_programs/add', methods=['GET', 'POST'])
def add_workout_program():
    form = WorkoutProgramForm()
    if form.validate_on_submit():
        exercises_json_data = request.form.get('exercises_json_data') # Get from hidden field
        exercises_json = None
        if exercises_json_data:
            try:
                exercises_data = json.loads(exercises_json_data)
                # Basic validation: Check if it's a dict with an 'exercises' list
                if isinstance(exercises_data, dict) and isinstance(exercises_data.get('exercises'), list):
                    # Further validation could check keys within each exercise item
                    exercises_json = exercises_data
                else:
                    raise ValueError("JSON must be a dictionary with an 'exercises' list.")
            except (json.JSONDecodeError, ValueError) as json_e:
                flash(f'Invalid JSON format submitted for exercises: {json_e}', 'danger')
                # Re-render with error, keep existing form data if possible
                return render_template('programs/add_edit.html', form=form, title="Add Workout Program")
        else:
             # Handle case where exercises might be optional or validation failed client-side
             flash('No exercise data submitted.', 'warning') # Or make exercises required?

        program = WorkoutProgram(
            name=form.name.data,
            date=form.date.data,
            team_id=form.assign_to_team.data or None,
            client_id=form.assign_to_client.data or None,
            notes=form.notes.data,
            exercises_json=exercises_json # Use parsed JSON
        )

        if not program.team_id and not program.client_id:
             flash('Program must be assigned to a team or a player.', 'warning')
             return render_template('programs/add_edit.html', form=form, title="Add Workout Program")

        db.session.add(program)
        try:
            db.session.commit()
            flash(f'Workout Program "{program.name}" created for {program.date.strftime("%Y-%m-%d")}.', 'success')
            return redirect(url_for('list_workout_programs'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating workout program: {e}")
            flash(f'Error creating program: {e}', 'danger')

    # Pass categories for the builder JS
    workout_categories = [cat.value for cat in WorkoutCategoryEnum]
    return render_template('programs/add_edit.html', form=form, title="Add Workout Program", workout_categories=workout_categories)


@app.route('/workout_programs/edit/<int:program_id>', methods=['GET', 'POST'])
def edit_workout_program(program_id):
    program = WorkoutProgram.query.get_or_404(program_id)
    form = WorkoutProgramForm(obj=program)

    if form.validate_on_submit():
        exercises_json_data = request.form.get('exercises_json_data') # Get from hidden field
        exercises_json = None
        if exercises_json_data:
            try:
                exercises_data = json.loads(exercises_json_data)
                if isinstance(exercises_data, dict) and isinstance(exercises_data.get('exercises'), list):
                    exercises_json = exercises_data
                else:
                     raise ValueError("JSON must be a dictionary with an 'exercises' list.")
            except (json.JSONDecodeError, ValueError) as json_e:
                flash(f'Invalid JSON format submitted for exercises: {json_e}', 'danger')
                # Pass current program data to pre-fill form again
                workout_categories = [cat.value for cat in WorkoutCategoryEnum]
                # Pass existing JSON back to JS if editing failed validation
                existing_json_str = json.dumps(program.exercises_json) if program.exercises_json else 'null'
                return render_template('programs/add_edit.html', form=form, title="Edit Workout Program", program=program, workout_categories=workout_categories, existing_exercises_json=existing_json_str)

        program.name = form.name.data
        program.date = form.date.data
        program.team_id = form.assign_to_team.data or None
        program.client_id = form.assign_to_client.data or None
        program.notes = form.notes.data
        program.exercises_json = exercises_json # Update with new JSON

        if not program.team_id and not program.client_id:
             flash('Program must be assigned to a team or a player.', 'warning')
             workout_categories = [cat.value for cat in WorkoutCategoryEnum]
             existing_json_str = json.dumps(program.exercises_json) if program.exercises_json else 'null'
             return render_template('programs/add_edit.html', form=form, title="Edit Workout Program", program=program, workout_categories=workout_categories, existing_exercises_json=existing_json_str)

        try:
            db.session.commit()
            flash(f'Workout Program "{program.name}" updated.', 'success')
            return redirect(url_for('list_workout_programs'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating workout program {program_id}: {e}")
            flash(f'Error updating program: {e}', 'danger')

    # Pre-fill form for GET request
    workout_categories = [cat.value for cat in WorkoutCategoryEnum]
    # Pass existing JSON to JS for pre-population
    existing_json_str = json.dumps(program.exercises_json) if program.exercises_json else 'null'
    return render_template('programs/add_edit.html', form=form, title="Edit Workout Program", program=program, workout_categories=workout_categories, existing_exercises_json=existing_json_str)


@app.route('/workout_programs/delete/<int:program_id>', methods=['POST'])
def delete_workout_program(program_id):
    program = WorkoutProgram.query.get_or_404(program_id)
    program_name = program.name
    # Check if linked to training sessions?
    sessions_count = TrainingSession.query.filter_by(workout_program_id=program_id).count()
    if sessions_count > 0:
         flash(f'Cannot delete program "{program_name}" as it is linked to {sessions_count} logged training session(s).', 'warning')
         return redirect(url_for('list_workout_programs'))
    try:
        db.session.delete(program)
        db.session.commit()
        flash(f'Workout Program "{program_name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting workout program {program_id}: {e}")
        flash(f'Error deleting program: {e}', 'danger')
    return redirect(url_for('list_workout_programs'))

# -- Training Sessions --
@app.route('/clients/<int:client_id>/add_training_session', methods=['GET', 'POST'])
def add_training_session(client_id):
    client = Client.query.get_or_404(client_id)
    form = TrainingSessionForm(client_id=client_id) # Pass client_id to form

    # Pre-fill logs JSON from selected program if adding new?
    # This is complex - requires JS or a separate step after selecting the program.
    # Keeping manual JSON entry for now.

    if form.validate_on_submit():
        logs_json = None
        # Should have a dedicated field in TrainingSessionForm for logs, not generic text
        # Assuming form.logs_json_text for now based on previous code
        if form.logs_json_text.data:
            try:
                logs_data = json.loads(form.logs_json_text.data)
                # Basic validation
                if isinstance(logs_data, dict) and isinstance(logs_data.get('logs'), list):
                    logs_json = logs_data
                else:
                    raise ValueError("JSON must be a dictionary with a 'logs' list.")
            except (json.JSONDecodeError, ValueError) as json_e:
                flash(f'Invalid JSON format for session logs: {json_e}', 'danger')
                # Re-render form with error
                json_instructions = "Enter session logs as JSON..." # Simplified
                return render_template('data_entry/generic_form.html', form=form, title="Log Training Session", client=client, json_instructions=json_instructions)


        session = TrainingSession(
            client_id=client_id,
            date=form.date.data,
            workout_program_id=form.workout_program_id.data or None,
            duration_minutes=form.duration_minutes.data,
            session_rpe=form.session_rpe.data,
            session_rating=form.session_rating.data,
            logs=logs_json
        )
        db.session.add(session)
        try:
            db.session.commit()
            flash(f'Training session for {session.date.strftime("%Y-%m-%d")} logged.', 'success')
            return redirect(url_for('view_client', client_id=client_id, _anchor='sessions'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error logging session for client {client_id}: {e}")
            flash(f'Error logging session: {e}', 'danger')

    # JSON instructions for the generic form template
    json_instructions = (
        "Enter session logs as JSON, e.g.:\n"
        '{\n'
        '  "session_rpe": 8,\n'
        '  "session_rating": 4,\n'
        '  "logs": [\n'
        '    { "exercise_id": 1, "set": 1, "weight": 100, "reps": 8, "velocity": null, "rpe": 7, "notes": "Good form" },\n'
        '    { "exercise_id": 1, "set": 2, "weight": 100, "reps": 8, ... },\n'
        '    ...\n'
        '  ]\n'
        '}'
    )
    return render_template('data_entry/generic_form.html', form=form, title="Log Training Session", client=client, json_instructions=json_instructions)


# TODO: View/Edit/Delete Training Session routes

# -- Reports --
@app.route('/reports', methods=['GET', 'POST'])
def generate_report():
    form = ReportForm()
    if form.validate_on_submit():
        report_type = form.report_type.data
        entity_id = form.client_id.data if report_type == 'client' else form.team_id.data
        start_date_req = form.start_date.data
        end_date_req = form.end_date.data

        if not entity_id:
            flash('Please select a player or team.', 'warning')
            return render_template('reports/generate.html', form=form)

        if start_date_req > end_date_req:
            flash('Start date cannot be after end date.', 'warning')
            return render_template('reports/generate.html', form=form)

        app.logger.info(f"Generating report: type={report_type}, id={entity_id}, start={start_date_req}, end={end_date_req}")

        try:
            # Fetch data
            report_context = get_report_data(report_type, entity_id, start_date_req, end_date_req)
            if not report_context:
                 flash('Error fetching report data or no data found for the selected criteria.', 'danger')
                 return render_template('reports/generate.html', form=form)

            # Generate PDF
            pdf_bytes = generate_report_pdf(report_context)

            if pdf_bytes:
                # Determine filename
                if report_type == 'client':
                    # Ensure client object exists before accessing name
                    client_name = report_context.get('client').name if report_context.get('client') else 'unknown_client'
                    filename_entity = client_name.replace(' ', '_')
                else:
                     # Ensure team object exists before accessing name
                    team_name = report_context.get('team').name if report_context.get('team') else 'unknown_team'
                    filename_entity = team_name.replace(' ', '_')

                filename = f"report_{filename_entity}_{start_date_req}_{end_date_req}.pdf"
                safe_filename = secure_filename(filename) # Sanitize filename

                app.logger.info(f"Successfully generated PDF: {safe_filename}")
                return Response(
                    pdf_bytes,
                    mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment;filename={safe_filename}"}
                )
            else:
                app.logger.error(f"Failed to generate PDF bytes for report: type={report_type}, id={entity_id}")
                flash('Failed to generate PDF report. Check logs for details.', 'danger')

        except Exception as e:
            app.logger.error(f"Unhandled error during report generation: {e}", exc_info=True)
            flash(f"An unexpected error occurred during report generation: {e}", 'danger')

    # Pre-populate dates (e.g., last 30 days)
    if request.method == 'GET' and not form.is_submitted(): # Avoid overriding POST data
        form.end_date.data = date.today()
        form.start_date.data = date.today() - timedelta(days=30)

    return render_template('reports/generate.html', form=form)

# --- API Endpoints (Optional - e.g., for dynamic forms/charts) ---
@app.route('/api/teams/<int:team_id>/players')
def api_get_team_players(team_id):
    # Ensure team exists
    team = Team.query.get_or_404(team_id)
    players = [{'id': p.id, 'name': p.name} for p in team.players]
    return jsonify(players)

@app.route('/api/exercises')
def api_get_exercises():
    try:
        exercises = Exercise.query.order_by(Exercise.name).all()
        exercise_list = [{'id': ex.id, 'name': ex.name, 'video_url': ex.video_url} for ex in exercises]
        return jsonify(exercise_list)
    except Exception as e:
        app.logger.error(f"API Error fetching exercises: {e}")
        return jsonify({"error": "Could not fetch exercises"}), 500

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback() # Rollback db session in case of internal error
    app.logger.error(f"Server Error: {error}", exc_info=True)
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    app.logger.info("Starting SOLAPP...")
    # Consider using environment variables for host/port/debug
    app.run(debug=app.config.get('DEBUG', False),
            host=app.config.get('HOST', '127.0.0.1'),
            port=app.config.get('PORT', 5000))
    # Turn off debug=True for any real deployment scenario