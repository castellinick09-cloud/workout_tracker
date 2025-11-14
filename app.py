import sqlite3
import json
import os
from flask import Flask, render_template, request, jsonify, g

# --- Configuration ---
app = Flask(__name__)
# The database file used for local development (SQLite)
DATABASE = 'workouts.db'

# --- Database Helper Functions ---

# Helper to connect to the SQLite database
def get_sqlite_db():
    db = getattr(g, '_sqlite_database', None)
    if db is None:
        db = g._sqlite_database = sqlite3.connect(DATABASE)
        # This makes the database return dictionary-like rows
        db.row_factory = sqlite3.Row
    return db

# Gets the database connection (or creates one)
def get_db():
    """
    Checks for a PostgreSQL URL (used in production) or falls back to SQLite (local dev).
    For now, since the app uses raw sqlite3 commands, we MUST fall back to SQLite.
    A future version (with SQLAlchemy) would handle PostgreSQL here.
    """
    return get_sqlite_db()

# Closes the database connection at the end of the request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_sqlite_database', None)
    if db is not None:
        db.close()

# --- One-Time Database Setup ---

# A function to create our database tables
def simple_init_db():
    """Initializes the SQLite database with the 'workouts' table."""
    sql_command = """
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_text TEXT NOT NULL,
        workout_json TEXT NOT NULL
    );
    """
    try:
        with app.app_context():
            db = get_db()
            db.cursor().executescript(sql_command)
            db.commit()
    except Exception as e:
        # This will catch errors if the table already exists, which is fine
        print(f"Database initialization failed: {e}")

# Call the init function once when the app starts
simple_init_db()


# --- Routes ---

# 1. The main entry point route
@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

# 2. The API for loading all past workouts
@app.route('/api/load_workouts', methods=['GET'])
def load_workouts():
    """Loads all saved workouts from the DB and returns them as a JSON list."""
    
    db = get_db()
    
    # Select all rows
    rows = db.execute('SELECT id, date_text, workout_json FROM workouts ORDER BY date_text DESC').fetchall()
    
    all_workouts = []
    for row in rows:
        # 'row' is a dictionary-like object
        # We parse the JSON text back into a real object
        workout_data = json.loads(row['workout_json'])
        
        # We ensure the original ID and Date are used
        workout_data = {
            'id': row['id'],
            'date': row['date_text'],
            **workout_data  # Merge the JSON contents into the main object
        }
        all_workouts.append(workout_data)
        
    return jsonify(all_workouts)

# 3. The API for saving a workout
@app.route('/api/save_workout', methods=['POST'])
def save_workout():
    """Receives workout data (as JSON) from the client and saves it to the DB."""
    
    # Get the JSON object sent from the front-end
    workout_data = request.get_json()
    
    # Store the two key pieces of data
    date_text = workout_data.get('date', '')
    # We store the *entire* workout object (including exercises and sets) as JSON text
    # This is simple and flexible.
    workout_json = json.dumps(workout_data)
    
    # Insert into the database
    db = get_db()
    cursor = db.execute(
        'INSERT INTO workouts (date_text, workout_json) VALUES (?, ?)',
        (date_text, workout_json)
    )
    db.commit()
    
    # Return the new ID back to the client
    new_id = cursor.lastrowid
    
    return jsonify({"success": True, "id": new_id})

# 4. The API for deleting a workout
@app.route('/api/delete_workout/<int:workout_id>', methods=['DELETE'])
def delete_workout(workout_id):
    """Deletes a workout by its ID."""
    
    db = get_db()
    db.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
    db.commit()
    
    return jsonify({"success": True})


if __name__ == '__main__':
    # When running locally, Flask uses this function.
    # When deployed, Gunicorn takes over and ignores this block.
    app.run(debug=True)