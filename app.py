import sqlite3
import json
from flask import Flask, render_template, request, jsonify, g

# --- Configuration ---
app = Flask(__name__)
DATABASE = 'workouts.db'

# --- Database Helper Functions ---

# Gets the database connection (or creates one)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # This makes the database return dictionaries, which is very helpful
        db.row_factory = sqlite3.Row
    return db

# Closes the database connection at the end of the request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    # FIX: Changed 'is not in None' to the correct Python syntax 'is not None'
    if db is not None:
        db.close()

# --- One-Time Database Setup ---

# A function to create our database tables
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# We need a 'schema.sql' file for the command above. 
# OR, to make it simple, let's just put the SQL right in the function.
# (This is simpler for you)
def simple_init_db():
    sql_command = """
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_text TEXT NOT NULL,
        workout_json TEXT NOT NULL
    );
    """
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    cursor.execute(sql_command)
    db.commit()
    db.close()
    print("Database initialized!")

# Add a terminal command to run this setup
@app.cli.command('init-db')
def init_db_command():
    """Clears the existing data and creates new tables."""
    simple_init_db()
    print('Initialized the database.')

# === API Endpoints (The "Brain") ===

# 1. The Main Page (Serves your app)
@app.route('/')
def index():
    """Serves the main index.html file to your phone's browser."""
    return render_template('index.html')

# 2. The API for getting workouts
@app.route('/api/get_workouts', methods=['GET'])
def get_workouts():
    """Fetches all workouts from the DB and returns them as JSON."""
    db = get_db()
    cursor = db.execute('SELECT * FROM workouts ORDER BY id DESC')
    rows = cursor.fetchall()
    
    all_workouts = []
    for row in rows:
        # 'row' is a dictionary-like object
        # We parse the JSON text back into a real object
        workout_data = json.loads(row['workout_json'])
        
        # We ensure the original ID and Date are used
        workout_data['id'] = row['id']
        workout_data['date'] = row['date_text']
        all_workouts.append(workout_data)
        
    return jsonify(all_workouts)

# 3. The API for saving a workout
@app.route('/api/save_workout', methods=['POST'])
def save_workout():
    """Receives workout data (as JSON) from the phone and saves it to the DB."""
    
    # Get the JSON object sent from the front-end
    workout_data = request.get_json()
    
    # Store the two key pieces of data
    date_text = workout_data.get('date', '')
    # We store the *entire* workout object (including exercises and sets) as JSON text
    # This is simple and flexible.
    workout_json = json.dumps(workout_data)
    
    # Insert into the database
    db = get_db()
    db.execute(
        'INSERT INTO workouts (date_text, workout_json) VALUES (?, ?)',
        (date_text, workout_json)
    )
    db.commit()
    
    return jsonify({"success": True, "message": "Workout saved!"})


# --- Run the App ---
if __name__ == '__main__':
    # 'host="0.0.0.0"' is CRITICAL. 
    # It makes the server accessible on your network, not just on your computer.
    app.run(debug=True, host='0.0.0.0', port=5000)