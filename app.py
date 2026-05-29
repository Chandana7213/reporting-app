import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from google.cloud.sql.connector import Connector
import pg8000.dbapi

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# === CLOUD STORAGE SETUP ===
BUCKET_NAME = os.getenv('BUCKET_NAME')
if BUCKET_NAME:
    from google.cloud import storage
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(BUCKET_NAME)
else:
    bucket = None
    os.makedirs('local_uploads', exist_ok=True)

# === CLOUD SQL SETUP ===
INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME')
DB_NAME = os.getenv('DB_NAME', 'reportdb')
DB_USER = os.getenv('DB_USER', 'reportuser')
DB_PASSWORD = os.getenv('DB_PASSWORD')

sql_connector = None
if INSTANCE_CONNECTION_NAME and DB_PASSWORD:
    try:
        sql_connector = Connector()
    except Exception as e:
        print(f"Warning: Could not initialize SQL connector: {e}")
        sql_connector = None

def get_sql_connection():
    """Get a database connection using the Cloud SQL connector."""
    if not sql_connector or not INSTANCE_CONNECTION_NAME or not DB_PASSWORD:
        return None
    try:
        conn = sql_connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            db=DB_NAME,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_status():
    """Get status of cloud integrations."""
    status = {
        'storage': 'enabled' if BUCKET_NAME else 'local fallback',
        'bucket': BUCKET_NAME or 'local_uploads/',
        'database': 'enabled' if sql_connector and INSTANCE_CONNECTION_NAME else 'not configured',
        'instance': INSTANCE_CONNECTION_NAME or 'N/A',
        'time': datetime.utcnow().isoformat()
    }
    return status

# === ROUTES ===

@app.route('/')
def home():
    """Home page with upload form and status."""
    status = get_status()
    return render_template('index.html', status=status)

@app.route('/upload', methods=['POST'])
def upload():
    """Handle file upload to Cloud Storage or local folder."""
    if 'report' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('home'))
    
    file = request.files['report']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('home'))
    
    filename = file.filename
    file_content = file.read()
    file_size = len(file_content)
    gcs_path = None
    
    # Save to Cloud Storage or local folder
    if bucket:
        try:
            blob = bucket.blob(filename)
            blob.upload_from_string(file_content, content_type=file.content_type)
            gcs_path = f"gs://{BUCKET_NAME}/{filename}"
            
            # Log the upload to Cloud SQL
            try:
                conn = get_sql_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO uploads (filename, gcs_path, size_bytes)
                        VALUES (%s, %s, %s)
                        """
                    , (filename, gcs_path, file_size))
                    conn.commit()
                    cursor.close()
                    conn.close()
            except Exception as db_error:
                print(f"Warning: Could not log upload to database: {db_error}")
            
            flash(f'Uploaded successfully to: {gcs_path}', 'success')
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
    else:
        try:
            local_path = os.path.join('local_uploads', filename)
            with open(local_path, 'wb') as f:
                f.write(file_content)
            
            # Log to database even for local mode
            try:
                conn = get_sql_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO uploads (filename, gcs_path, size_bytes)
                        VALUES (%s, %s, %s)
                        """
                    , (filename, local_path, file_size))
                    conn.commit()
                    cursor.close()
                    conn.close()
            except Exception as db_error:
                print(f"Warning: Could not log upload to database: {db_error}")
            
            flash(f'Uploaded successfully to: {local_path}', 'success')
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
    
    return redirect(url_for('home'))

@app.route('/uploads')
def view_uploads():
    """Display all uploaded files from the database."""
    status = get_status()
    uploads = []
    error = None
    
    try:
        conn = get_sql_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, filename, gcs_path, size_bytes, uploaded_at
                FROM uploads
                ORDER BY uploaded_at DESC
                """
            )
            rows = cursor.fetchall()
            
            for row in rows:
                uploads.append({
                    'id': row[0],
                    'filename': row[1],
                    'gcs_path': row[2],
                    'size_bytes': row[3],
                    'uploaded_at': row[4],
                    'size_mb': round(row[3] / (1024*1024), 2) if row[3] else 0
                })
            
            cursor.close()
            conn.close()
        else:
            error = 'Database not configured'
    except Exception as e:
        error = f'Error fetching uploads: {str(e)}'
        print(f"Database error: {e}")
    
    return render_template('uploads.html', uploads=uploads, status=status, error=error)

@app.route('/dbtest')
def dbtest():
    """Test the Cloud SQL connection."""
    status = get_status()
    try:
        conn = get_sql_connection()
        if not conn:
            return f'Database connection FAILED: not configured', 500
        
        cursor = conn.cursor()
        cursor.execute('SELECT NOW();')
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        server_time = result[0] if result else 'Unknown'
        return f'Database connection OK. Server time: {server_time}', 200
    except Exception as e:
        error_details = str(e)
        if hasattr(e, 'args'):
            try:
                error_obj = json.loads(str(e.args[0]))
                error_details = error_obj.get('M', str(e))
            except:
                error_details = str(e)
        return f'Database connection FAILED: {error_details}', 500

@app.route('/healthz')
def healthz():
    """Health check endpoint."""
    return 'ok', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=True)