from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timezone

app = Flask(__name__)

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def handle_error(error_msg, details=None, status_code=500):
    response = {'error': error_msg}
    if DEBUG_MODE and details:
        response['details'] = details
    return jsonify(response), status_code

@app.route('/log', methods=['POST'])
def log_visit():
    conn = None
    cur = None
    
    try:
        data = request.get_json()
        
        if not data:
            return handle_error('Request body is required', None, 400)
        
        code = data.get('code')
        
        if not code:
            return handle_error('Code is required', None, 400)
        
        ip_address = data.get('ip_address', request.remote_addr)
        user_agent = data.get('user_agent', request.headers.get('User-Agent', 'unknown'))
        visited_at = datetime.now(timezone.utc)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO visits (code, ip_address, user_agent, visited_at) 
               VALUES (%s, %s, %s, %s)""",
            (code, ip_address, user_agent, visited_at)
        )
        conn.commit()
        
        return jsonify({
            'status': 'logged',
            'code': code,
            'visited_at': visited_at.isoformat()
        }), 200
        
    except psycopg2.Error as e:
        return handle_error('Database error', str(e) if DEBUG_MODE else None, 500)
    except Exception as e:
        return handle_error('Internal server error', str(e) if DEBUG_MODE else None, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/stats/<code>', methods=['GET'])
def get_stats(code):
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT COUNT(*) as total_visits FROM visits WHERE code = %s",
            (code,)
        )
        result = cur.fetchone()
        
        return jsonify({
            'code': code,
            'total_visits': result['total_visits'] if result else 0
        }), 200
        
    except psycopg2.Error as e:
        return handle_error('Database error', str(e) if DEBUG_MODE else None, 500)
    except Exception as e:
        return handle_error('Internal server error', str(e) if DEBUG_MODE else None, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/health', methods=['GET'])
def health():
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        db_status = 'connected'
    except:
        db_status = 'disconnected'
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return jsonify({
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'service': 'logger',
        'database': db_status,
        'debug_mode': DEBUG_MODE,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200 if db_status == 'connected' else 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)