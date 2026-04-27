from flask import Flask, request, jsonify, redirect
import psycopg2
import os
import random
import string
import requests
from datetime import datetime, timezone

app = Flask(__name__)

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'false').lower() == 'true'

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def is_valid_url(url):
    return url.startswith(('http://', 'https://'))

def get_unique_code(max_attempts=5):
    for attempt in range(max_attempts):
        code = generate_short_code()
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM urls WHERE code = %s", (code,))
        exists = cur.fetchone()
        cur.close()
        conn.close()
        
        if not exists:
            return code
    
    raise Exception("Failed to generate unique code after 5 attempts")

def log_visit_to_logger(code, ip_address, user_agent):
    try:
        logger_url = os.environ.get('LOGGER_URL', 'http://logger:5001')
        requests.post(
            f"{logger_url}/log",
            json={'code': code, 'ip_address': ip_address, 'user_agent': user_agent},
            timeout=2
        )
    except Exception as e:
        if DEBUG_MODE:
            print(f"Failed to log visit: {e}")

def handle_error(error_msg, details=None, status_code=500):
    response = {'error': error_msg}
    if DEBUG_MODE and details:
        response['details'] = details
    return jsonify(response), status_code

@app.route('/shorten', methods=['POST'])
def shorten_url():
    conn = None
    cur = None
    
    try:
        data = request.get_json()
        if not data:
            return handle_error('Request body is required', None, 400)
        
        long_url = data.get('long_url')
        if not long_url:
            return handle_error('long_url is required', None, 400)
        
        if not is_valid_url(long_url):
            return handle_error('URL must start with http:// or https://', None, 400)
        
        code = get_unique_code()
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO urls (code, long_url, created_at) VALUES (%s, %s, %s)",
            (code, long_url, datetime.now(timezone.utc))
        )
        conn.commit()
        
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        
        return jsonify({
            'short_url': f"{base_url}/{code}",
            'code': code,
            'long_url': long_url
        }), 201
        
    except psycopg2.Error as e:
        return handle_error('Database error', str(e) if DEBUG_MODE else None, 500)
    except Exception as e:
        return handle_error('Internal server error', str(e) if DEBUG_MODE else None, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/<code>', methods=['GET'])
def redirect_to_long_url(code):
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT long_url FROM urls WHERE code = %s", (code,))
        result = cur.fetchone()
        
        if not result:
            return handle_error('URL not found', None, 404)
        
        long_url = result[0]
        
        log_visit_to_logger(
            code=code,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', 'unknown')
        )
        
        return redirect(long_url, code=302)
        
    except Exception as e:
        return handle_error('Internal server error', str(e) if DEBUG_MODE else None, 500)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.route('/stats/<code>', methods=['GET'])
def get_stats(code):
    try:
        logger_url = os.environ.get('LOGGER_URL', 'http://logger:5001')
        response = requests.get(f"{logger_url}/stats/{code}", timeout=5)
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return handle_error('Logger service unavailable', str(e) if DEBUG_MODE else None, 503)
    except Exception as e:
        return handle_error('Internal server error', str(e) if DEBUG_MODE else None, 500)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'shortener',
        'debug_mode': DEBUG_MODE,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)