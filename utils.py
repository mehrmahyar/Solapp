import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from models import db, Baseline, TestTypeEnum, get_baseline_value, Readiness, Client, Team, BodyComposition, PhysicalTest, TrainingSession
from config import Config
from datetime import date, timedelta
import os
import uuid
from weasyprint import HTML, CSS
from flask import render_template

def calculate_readiness_score(readiness_entry):
    """Calculates readiness score based on the Readiness entry and configured weights."""
    client_id = readiness_entry.client_id
    weights = Config.READINESS_WEIGHTS
    score = 0
    total_weight = 0

    # Subjective Scores (Normalized 0-10, assuming 1-5 input scale)
    # Higher input is better (e.g., 5 = Best/No soreness)
    factors = {
        'sleep': readiness_entry.sleep_quality,       # Needs special handling for duration vs quality
        'fatigue': readiness_entry.fatigue_level,
        'soreness': readiness_entry.muscle_soreness,
        'mood': readiness_entry.mood,
        'stress': readiness_entry.stress_level,
        'confidence': readiness_entry.confidence
    }

    for key, value in factors.items():
        if value is not None and key in weights:
            normalized_score = (value - 1) * 2.5 # Scale 1-5 to 0-10
            score += normalized_score * weights[key]
            total_weight += weights[key]

    # Sleep Duration (Special handling - normalized to 8 hours = 10 points)
    if readiness_entry.sleep_duration is not None and 'sleep' in weights: # Using 'sleep' weight for duration too
        sleep_norm = min(readiness_entry.sleep_duration / 8.0, 1.25) * 10 # Cap bonus sleep, scale to 10
        # Let's average sleep quality and duration score contribution if both exist
        # This is debatable, could use separate weights or prioritize one
        if 'sleep' in factors and factors['sleep'] is not None:
             # Adjust existing score: remove quality part, add average part
             qual_score = (factors['sleep'] - 1) * 2.5
             score -= qual_score * weights['sleep']
             avg_sleep_score = (qual_score + sleep_norm) / 2
             score += avg_sleep_score * weights['sleep']
             # total_weight already counted
        else:
            # Only duration available
            score += sleep_norm * weights['sleep']
            if 'sleep' not in factors or factors['sleep'] is None:
                 total_weight += weights['sleep'] # Add weight if quality wasn't counted

    # Objective Scores (CMJ, Drop Jump) - % of baseline
    cmj_baseline_val = get_baseline_value(client_id, TestTypeEnum.CMJ)
    if readiness_entry.cmj_result is not None and cmj_baseline_val and 'cmj' in weights:
        cmj_ratio = readiness_entry.cmj_result / cmj_baseline_val
        # Cap ratio to avoid extreme scores, e.g., max 120% = 12 points
        cmj_score = min(cmj_ratio, 1.2) * 10
        score += cmj_score * weights['cmj']
        total_weight += weights['cmj']

    drop_jump_baseline_val = get_baseline_value(client_id, TestTypeEnum.DROP_JUMP)
    if readiness_entry.drop_jump_result is not None and drop_jump_baseline_val and 'drop_jump' in weights:
        dj_ratio = readiness_entry.drop_jump_result / drop_jump_baseline_val
        dj_score = min(dj_ratio, 1.2) * 10
        score += dj_score * weights['drop_jump']
        total_weight += weights['drop_jump']

    # Handle Injury/Pain - Penalize score significantly if pain is reported
    if readiness_entry.injury_pain:
        score *= 0.7 # Apply a 30% penalty, configurable

    # Final score calculation (normalized to 100)
    if total_weight > 0:
        final_score = (score / (total_weight * 10)) * 100 # Max possible score is total_weight * 10
        return round(max(0, min(final_score, 100)), 1) # Clamp between 0 and 100
    else:
        return 0 # Or None, if no data was available

# --- Plotting Functions ---

def create_readiness_plot(client_id, start_date, end_date):
    readiness_data = Readiness.query.filter(
        Readiness.client_id == client_id,
        Readiness.date >= start_date,
        Readiness.date <= end_date
    ).order_by(Readiness.date).all()

    if not readiness_data:
        return None

    df = pd.DataFrame([{ 
        'date': r.date,
        'score': r.calculated_readiness_score or calculate_readiness_score(r),
        'sleep_quality': r.sleep_quality,
        'sleep_duration': r.sleep_duration,
        'soreness': r.muscle_soreness,
        'fatigue': r.fatigue_level,
        'mood': r.mood,
        'stress': r.stress_level,
        'confidence': r.confidence
    } for r in readiness_data])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1,
                        subplot_titles=('Readiness Score Trend', 'Subjective Factors (1-5 Scale)'))

    fig.add_trace(go.Scatter(x=df['date'], y=df['score'], mode='lines+markers',
                           name='Readiness Score', line=dict(color='#1f77b4')),
                  row=1, col=1)

    factors = ['sleep_quality', 'soreness', 'fatigue', 'mood', 'stress', 'confidence']
    colors = ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']

    for factor, color in zip(factors, colors):
        fig.add_trace(go.Scatter(x=df['date'], y=df[factor], mode='lines+markers',
                               name=factor.replace('_', ' ').title(), line=dict(color=color)),
                      row=2, col=1)

    fig.update_layout(title_text=f'Readiness Overview ({start_date} to {end_date})',
                      legend_title_text='Metrics', height=600)
    fig.update_yaxes(title_text="Score (0-100)", row=1, col=1)
    fig.update_yaxes(title_text="Rating (1-5)", range=[0.5, 5.5], row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return fig

def create_body_composition_plot(client_id, start_date, end_date):
    comp_data = BodyComposition.query.filter(
        BodyComposition.client_id == client_id,
        BodyComposition.date >= start_date,
        BodyComposition.date <= end_date
    ).order_by(BodyComposition.date).all()

    if not comp_data:
        return None

    df = pd.DataFrame([{ 
        'date': r.date,
        'weight': r.weight,
        'body_fat': r.body_fat,
        'muscle_mass': r.muscle_mass
    } for r in comp_data])

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.05,
                        subplot_titles=('Weight (kg)', 'Body Fat (%)', 'Muscle Mass (kg)'))

    fig.add_trace(go.Scatter(x=df['date'], y=df['weight'], mode='lines+markers', name='Weight'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['body_fat'], mode='lines+markers', name='Body Fat'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['muscle_mass'], mode='lines+markers', name='Muscle Mass'), row=3, col=1)

    fig.update_layout(title_text=f'Body Composition ({start_date} to {end_date})', showlegend=False, height=700)
    fig.update_xaxes(title_text="Date", row=3, col=1)

    return fig

def create_physical_test_plot(client_id, test_type_enum, start_date, end_date):
    test_data = PhysicalTest.query.filter(
        PhysicalTest.client_id == client_id,
        PhysicalTest.test_type == test_type_enum,
        PhysicalTest.date >= start_date,
        PhysicalTest.date <= end_date
    ).order_by(PhysicalTest.date).all()

    if not test_data:
        return None

    # Attempt to parse values numerically where possible
    parsed_data = []
    for r in test_data:
        numeric_val = None
        try:
            if '/' in r.value:
                numeric_val = float(r.value.split('/')[0])
            elif 'Level' in r.value:
                numeric_val = float(r.value.split(' ')[-1])
            else:
                numeric_val = float(r.value)
        except (ValueError, TypeError):
            pass # Keep as None if not parseable
        parsed_data.append({'date': r.date, 'value': numeric_val, 'raw_value': r.value})

    df = pd.DataFrame(parsed_data)
    df_numeric = df.dropna(subset=['value']) # Only plot numeric data

    if df_numeric.empty:
        # Maybe display raw values if none are numeric?
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_numeric['date'], y=df_numeric['value'], mode='lines+markers',
                           name=test_type_enum.value,
                           text=df_numeric['raw_value'], # Show raw value on hover
                           hovertemplate=
                           '<b>Date</b>: %{x|%Y-%m-%d}<br>' +
                           '<b>Result</b>: %{text}<extra></extra>'
                           ))

    fig.update_layout(title_text=f'{test_type_enum.value} Trend ({start_date} to {end_date})',
                      xaxis_title='Date', yaxis_title='Result Value')

    return fig


# --- Report Generation Logic ---

# Ensure the directory for storing temporary plot images exists
PLOT_IMG_DIR = os.path.join(Config.basedir, 'instance', 'plot_images')
if not os.path.exists(PLOT_IMG_DIR):
    os.makedirs(PLOT_IMG_DIR)

def generate_report_pdf(report_context, template_name="reports/report_template.html"):
    """Generates a PDF report from context data and an HTML template."""

    # 1. Generate Plotly charts and save as images
    plot_filenames = {}
    if report_context.get('readiness_fig'):
        filename = f"readiness_{uuid.uuid4().hex}.png"
        filepath = os.path.join(PLOT_IMG_DIR, filename)
        try:
            report_context['readiness_fig'].write_image(filepath, scale=2) # Use kaleido
            plot_filenames['readiness_plot'] = filepath
        except Exception as e:
            print(f"Error saving readiness plot: {e}")
            plot_filenames['readiness_plot'] = None # Or a placeholder image path

    if report_context.get('body_comp_fig'):
        filename = f"bodycomp_{uuid.uuid4().hex}.png"
        filepath = os.path.join(PLOT_IMG_DIR, filename)
        try:
            report_context['body_comp_fig'].write_image(filepath, scale=2)
            plot_filenames['body_comp_plot'] = filepath
        except Exception as e:
             print(f"Error saving body comp plot: {e}")
             plot_filenames['body_comp_plot'] = None

    # Add more plots here (e.g., physical tests)
    test_plot_filenames = {}
    if report_context.get('test_figs'):
        for test_type_name, fig in report_context['test_figs'].items():
             if fig:
                filename = f"test_{test_type_name.replace(' ', '_')}_{uuid.uuid4().hex}.png"
                filepath = os.path.join(PLOT_IMG_DIR, filename)
                try:
                    fig.write_image(filepath, scale=2)
                    test_plot_filenames[test_type_name] = filepath
                except Exception as e:
                    print(f"Error saving test plot {test_type_name}: {e}")
                    test_plot_filenames[test_type_name] = None
    plot_filenames['test_plots'] = test_plot_filenames


    # 2. Render HTML template with data and image paths
    # Pass absolute file paths to the template for WeasyPrint to find them
    html_string = render_template(template_name, **report_context, plot_files=plot_filenames)

    # 3. Convert HTML to PDF using WeasyPrint
    try:
        # Define base_url for WeasyPrint to find relative paths if needed (e.g., CSS)
        # Here we use absolute paths for images, so it might not be strictly necessary
        # but good practice if linking static CSS.
        html = HTML(string=html_string, base_url=Config.basedir)

        # Add basic CSS for printing (consider a separate print.css)
        css_string = """
            @page {
                size: A4;
                margin: 1.5cm;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10pt;
                }
            }
            body { font-family: sans-serif; }
            h1, h2, h3 { color: #333; margin-bottom: 0.5em; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
            th, td { border: 1px solid #ccc; padding: 0.4em; text-align: left; }
            th { background-color: #eee; }
            .plot-container img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
            .no-data { font-style: italic; color: #888; }
        """
        css = CSS(string=css_string)

        pdf_bytes = html.write_pdf(stylesheets=[css])

        # 4. Clean up temporary image files
        for path in plot_filenames.values():
            if isinstance(path, str) and os.path.exists(path):
                os.remove(path)
            elif isinstance(path, dict):
                 for sub_path in path.values():
                      if isinstance(sub_path, str) and os.path.exists(sub_path):
                           os.remove(sub_path)

        return pdf_bytes

    except Exception as e:
        print(f"Error generating PDF: {e}")
        # Clean up any images that were created before the error
        for path in plot_filenames.values():
            if isinstance(path, str) and os.path.exists(path):
                os.remove(path)
            elif isinstance(path, dict):
                 for sub_path in path.values():
                      if isinstance(sub_path, str) and os.path.exists(sub_path):
                           os.remove(sub_path)
        return None

def get_report_data(report_type, entity_id, start_date, end_date):
    """Fetches data needed for reports."""
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'report_type': report_type
    }

    if report_type == 'client':
        client = Client.query.get_or_404(entity_id)
        context['client'] = client
        context['team'] = client.team
        client_ids = [client.id]
        context['report_title'] = f"Player Report: {client.name}"
    elif report_type == 'team':
        team = Team.query.get_or_404(entity_id)
        context['team'] = team
        client_ids = [p.id for p in team.players]
        context['report_title'] = f"Team Report: {team.name}"
        if not client_ids:
             return context # No players in team
    else:
        return None # Invalid type

    # Fetch data within the date range for the relevant client(s)
    context['readiness_data'] = Readiness.query.filter(
        Readiness.client_id.in_(client_ids),
        Readiness.date >= start_date,
        Readiness.date <= end_date
    ).order_by(Readiness.date).all()

    context['body_comp_data'] = BodyComposition.query.filter(
        BodyComposition.client_id.in_(client_ids),
        BodyComposition.date >= start_date,
        BodyComposition.date <= end_date
    ).order_by(BodyComposition.date).all()

    context['physical_test_data'] = PhysicalTest.query.filter(
        PhysicalTest.client_id.in_(client_ids),
        PhysicalTest.date >= start_date,
        PhysicalTest.date <= end_date
    ).order_by(PhysicalTest.date, PhysicalTest.test_type).all()

    context['training_session_data'] = TrainingSession.query.filter(
        TrainingSession.client_id.in_(client_ids),
        TrainingSession.date >= start_date,
        TrainingSession.date <= end_date
    ).order_by(TrainingSession.date).all()

    # --- Generate Figures for Report (only for client reports for now) ---
    if report_type == 'client':
        context['readiness_fig'] = create_readiness_plot(client.id, start_date, end_date)
        context['body_comp_fig'] = create_body_composition_plot(client.id, start_date, end_date)

        test_figs = {}
        # Generate plots for key physical tests
        key_tests = [TestTypeEnum.CMJ, TestTypeEnum.DROP_JUMP, TestTypeEnum.SPRINT_20YD, TestTypeEnum.YO_YO_IR1]
        for test_type in key_tests:
             fig = create_physical_test_plot(client.id, test_type, start_date, end_date)
             if fig:
                 test_figs[test_type.value] = fig
        context['test_figs'] = test_figs

    # Add aggregated data for team reports if needed (e.g., average readiness)
    # ... calculations using pandas on the fetched data ...

    return context 