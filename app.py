"""
Real Estate Agent - Full Property Manager with Applications & Payments
Run: python app.py  →  http://localhost:5000
"""

import os
import sqlite3
import uuid
from datetime import datetime
from urllib.parse import quote
from flask import (
    Flask, request, jsonify, render_template_string,
    g, send_from_directory, Response
)

# ============================================================
# CONFIGURATION
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'real_estate.db'))
UPLOAD_DIR = os.environ.get('UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads'))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---- WhatsApp ----
WHATSAPP_NUMBER = "15551234567"   # international format, no + or spaces
WHATSAPP_MESSAGE = "Hi Sarah! I'm interested in a property listing."

# ---- Payment ----
PAYMENT_AMOUNT = 50.00
PAYPAL_EMAIL = "sarah@andersonrealty.com"
ZELLE_EMAIL = "sarah@andersonrealty.com"
ZELLE_PHONE = "(555) 123-4567"

# ---- Agent profile ----
AGENT_NAME = "Sarah Anderson"
AGENT_TITLE = "Licensed Real Estate Agent"
AGENT_EMAIL = "sarah@andersonrealty.com"
AGENT_PHONE = "(555) 123-4567"
AGENT_BIO = ("With 12+ years of experience and over 340 successful transactions, "
             "I help families find the perfect place to call home — from first-time "
             "buyers to luxury estates.")
AGENT_YEARS = "12+"
AGENT_SALES = "340+"
AGENT_VOLUME = "$10M"

app = Flask(__name__)
app.config['DATABASE'] = DATABASE
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB


# ============================================================
# FAVICON (inline SVG, no external file)
# ============================================================
FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<rect width='100' height='100' rx='20' fill='#1a1a2e'/>"
    "<path d='M50 22 L78 46 L78 76 L60 76 L60 58 L40 58 L40 76 L22 76 L22 46 Z' "
    "fill='#e94560'/>"
    "</svg>"
)
FAVICON_DATA_URI = "data:image/svg+xml," + quote(FAVICON_SVG)

FAVICON_TAG = (
    f'<link rel="icon" type="image/svg+xml" href="{FAVICON_DATA_URI}">'
    f'<link rel="apple-touch-icon" href="{FAVICON_DATA_URI}">'
    f'<meta name="theme-color" content="#1a1a2e">'
)


# ============================================================
# DATABASE
# ============================================================
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL,
                address TEXT NOT NULL,
                bedrooms REAL DEFAULT 0,
                bathrooms REAL DEFAULT 0,
                sqft REAL DEFAULT 0,
                type TEXT,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER NOT NULL,
                reference TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                bio TEXT,
                employment TEXT,
                annual_income REAL DEFAULT 0,
                move_in_date TEXT,
                id_type TEXT,
                id_filename TEXT,
                payment_method TEXT,
                payment_status TEXT DEFAULT 'pending',
                payment_reference TEXT,
                application_status TEXT DEFAULT 'pending_payment',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (property_id) REFERENCES properties(id)
            )
        ''')
        conn.commit()

        if conn.execute('SELECT COUNT(*) FROM properties').fetchone()[0] == 0:
            seed = [
                ("Modern Downtown Apartment", 485000, "For Sale",
                 "123 Main Street, Downtown, New York, NY 10001", 3, 2, 1450, "Apartment",
                 "Stunning city views with modern finishes. Walk to all major attractions."),
                ("Suburban Family Home", 625000, "For Sale",
                 "456 Oak Avenue, Springfield, IL 62701", 4, 3, 2400, "House",
                 "Spacious family home with large backyard and top-rated schools."),
                ("Cozy Studio Rental", 1800, "For Rent",
                 "789 Elm Street, Midtown, San Francisco, CA 94102", 1, 1, 650, "Apartment",
                 "Fully furnished studio in prime location. Utilities included."),
                ("Luxury Waterfront Condo", 1200000, "Pending",
                 "321 Marina Boulevard, Miami, FL 33101", 3, 3.5, 2100, "Condo",
                 "Waterfront luxury with private balcony and marina views."),
                ("Charming Victorian Townhouse", 875000, "For Sale",
                 "55 Beacon Hill Road, Boston, MA 02108", 4, 2.5, 2200, "Townhouse",
                 "Historic charm meets modern updates."),
                ("Executive Penthouse Suite", 5500, "For Rent",
                 "1000 Skyline Drive, Austin, TX 78701", 3, 3, 2800, "Condo",
                 "Top-floor penthouse with panoramic city views."),
                ("Ranch-Style Country Home", 410000, "Sold",
                 "2874 Meadow Lane, Nashville, TN 37201", 3, 2, 1850, "House",
                 "Quiet country living on 2 acres with mature trees."),
                ("Beachfront Bungalow", 1450000, "For Sale",
                 "88 Oceanfront Way, Malibu, CA 90265", 2, 2, 1600, "House",
                 "Steps from the sand with private beach access."),
                ("Industrial Loft Downtown", 3200, "For Rent",
                 "444 Warehouse District, Denver, CO 80202", 2, 2, 1700, "Apartment",
                 "Converted industrial loft with exposed brick."),
                ("Garden View Condominium", 365000, "Pending",
                 "2121 Greenway Terrace, Portland, OR 97201", 2, 2, 1250, "Condo",
                 "Peaceful condo overlooking landscaped gardens."),
                ("Historic Brownstone", 1950000, "For Sale",
                 "342 Park Slope Avenue, Brooklyn, NY 11215", 5, 4, 3600, "Townhouse",
                 "Immaculately preserved 5-bedroom brownstone."),
                ("Lakefront Retreat", 720000, "Sold",
                 "91 Lakeshore Drive, Lake Tahoe, CA 96150", 4, 3, 2600, "House",
                 "Serene lakefront property with private dock."),
            ]
            conn.executemany('''
                INSERT INTO properties (title, price, status, address, bedrooms,
                                        bathrooms, sqft, type, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', seed)
            conn.commit()
            print(f"[INIT] Seeded {len(seed)} sample properties.")


# ============================================================
# SHARED WHATSAPP BUTTON (HTML + CSS)
# ============================================================
WHATSAPP_CSS = """
.whatsapp-float {
    position: fixed; bottom: 28px; right: 28px;
    width: 58px; height: 58px; background: #25D366;
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    box-shadow: 0 6px 20px rgba(37,211,102,0.5);
    z-index: 9999; text-decoration: none;
    transition: transform 0.25s ease;
    animation: wa-pulse 2s infinite;
}
.whatsapp-float:hover { transform: scale(1.1); animation: none; }
@keyframes wa-pulse {
    0%   { box-shadow: 0 6px 20px rgba(37,211,102,0.5), 0 0 0 0 rgba(37,211,102,0.6); }
    70%  { box-shadow: 0 6px 20px rgba(37,211,102,0.5), 0 0 0 18px rgba(37,211,102,0); }
    100% { box-shadow: 0 6px 20px rgba(37,211,102,0.5), 0 0 0 0 rgba(37,211,102,0); }
}
@media (max-width: 768px) {
    .whatsapp-float { width: 54px; height: 54px; bottom: 20px; right: 20px; }
}
"""


def whatsapp_button_html():
    link = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(WHATSAPP_MESSAGE)}"
    return f'''
    <a href="{link}" target="_blank" rel="noopener"
       class="whatsapp-float" aria-label="Chat on WhatsApp">
        <svg viewBox="0 0 32 32" width="30" height="30" fill="white">
            <path d="M19.11 17.205c-.372 0-1.088 1.39-1.518 1.39a.63.63 0 0 1-.315-.1c-.802-.402-1.504-.817-2.163-1.447-.545-.516-1.146-1.29-1.46-1.963a.426.426 0 0 1-.073-.215c0-.33.99-.945.99-1.49 0-.143-.73-2.09-.832-2.335-.143-.372-.214-.487-.6-.487-.187 0-.36-.043-.53-.043-.302 0-.53.115-.746.315-.688.645-1.032 1.318-1.06 2.264v.114c-.015.99.472 1.977 1.017 2.78 1.23 1.82 2.506 3.41 4.554 4.34.616.287 2.035.888 2.722.888.817 0 2.15-.515 2.478-1.318.13-.33.244-.73.244-1.088 0-.058 0-.144-.03-.215-.1-.1-2.434-1.39-2.678-1.39zm-2.908 7.593c-1.747 0-3.48-.53-4.942-1.49L7.793 24.41l1.132-3.337a8.955 8.955 0 0 1-1.72-5.272c0-4.955 4.04-8.995 8.997-8.995S25.2 10.845 25.2 15.8c0 4.958-4.04 8.998-8.998 8.998zm0-19.798c-5.96 0-10.8 4.842-10.8 10.802 0 1.964.53 3.898 1.546 5.574L5 27.176l5.974-1.92a10.807 10.807 0 0 0 16.03-9.455c0-5.958-4.842-10.8-10.802-10.8z"/>
        </svg>
    </a>
    '''


# ============================================================
# PROPERTY API
# ============================================================
@app.route('/api/properties', methods=['GET'])
def api_list_properties():
    db = get_db()
    status = request.args.get('status')
    search = request.args.get('search', '').strip()
    query = 'SELECT * FROM properties WHERE 1=1'
    params = []
    if status and status != 'all':
        query += ' AND status = ?'
        params.append(status)
    if search:
        query += ' AND (title LIKE ? OR address LIKE ?)'
        like = f'%{search}%'
        params.extend([like, like])
    query += ' ORDER BY created_at DESC'
    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/properties/<int:pid>', methods=['GET'])
def api_get_property(pid):
    db = get_db()
    row = db.execute('SELECT * FROM properties WHERE id = ?', (pid,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))


@app.route('/api/properties', methods=['POST'])
def api_create_property():
    data = request.get_json() or {}
    for f in ['title', 'price', 'status', 'address']:
        if not data.get(f):
            return jsonify({'error': f'Missing {f}'}), 400
    db = get_db()
    cur = db.execute('''
        INSERT INTO properties (title, price, status, address, bedrooms, bathrooms, sqft, type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['title'].strip(), float(data['price']), data['status'], data['address'].strip(),
          float(data.get('bedrooms', 0) or 0), float(data.get('bathrooms', 0) or 0),
          float(data.get('sqft', 0) or 0), data.get('type', 'House'),
          (data.get('description') or '').strip()))
    db.commit()
    row = db.execute('SELECT * FROM properties WHERE id = ?', (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route('/api/properties/<int:pid>', methods=['PUT'])
def api_update_property(pid):
    data = request.get_json() or {}
    db = get_db()
    if not db.execute('SELECT id FROM properties WHERE id = ?', (pid,)).fetchone():
        return jsonify({'error': 'Not found'}), 404
    fields = ['title', 'price', 'status', 'address', 'bedrooms', 'bathrooms', 'sqft', 'type', 'description']
    updates, params = [], []
    for f in fields:
        if f in data:
            updates.append(f'{f} = ?')
            params.append(float(data[f] or 0) if f in ('price', 'bedrooms', 'bathrooms', 'sqft') else data[f])
    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400
    updates.append('updated_at = ?')
    params.append(datetime.utcnow().isoformat())
    params.append(pid)
    db.execute(f'UPDATE properties SET {",".join(updates)} WHERE id = ?', params)
    db.commit()
    row = db.execute('SELECT * FROM properties WHERE id = ?', (pid,)).fetchone()
    return jsonify(dict(row))


@app.route('/api/properties/<int:pid>', methods=['DELETE'])
def api_delete_property(pid):
    db = get_db()
    db.execute('DELETE FROM applications WHERE property_id = ?', (pid,))
    db.execute('DELETE FROM properties WHERE id = ?', (pid,))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/stats', methods=['GET'])
def api_stats():
    db = get_db()
    return jsonify({
        'total': db.execute('SELECT COUNT(*) FROM properties').fetchone()[0],
        'for_sale': db.execute("SELECT COUNT(*) FROM properties WHERE status='For Sale'").fetchone()[0],
        'for_rent': db.execute("SELECT COUNT(*) FROM properties WHERE status='For Rent'").fetchone()[0],
        'total_value': db.execute('SELECT COALESCE(SUM(price),0) FROM properties').fetchone()[0],
        'applications': db.execute('SELECT COUNT(*) FROM applications').fetchone()[0],
        'paid_applications': db.execute("SELECT COUNT(*) FROM applications WHERE payment_status='paid'").fetchone()[0],
    })


# ============================================================
# APPLICATION API
# ============================================================
@app.route('/api/applications', methods=['POST'])
def api_create_application():
    db = get_db()
    property_id = request.form.get('property_id')
    if not property_id:
        return jsonify({'error': 'property_id required'}), 400

    prop = db.execute('SELECT * FROM properties WHERE id = ?', (property_id,)).fetchone()
    if not prop:
        return jsonify({'error': 'Property not found'}), 404

    for f in ['full_name', 'email', 'phone', 'bio', 'employment']:
        if not request.form.get(f, '').strip():
            return jsonify({'error': f'{f} is required'}), 400

    id_file = request.files.get('id_file')
    if not id_file or not id_file.filename:
        return jsonify({'error': 'ID document is required'}), 400

    ext = os.path.splitext(id_file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.pdf'):
        return jsonify({'error': 'ID must be JPG, PNG, or PDF'}), 400

    reference = 'APP-' + uuid.uuid4().hex[:8].upper()
    saved_name = f"{reference}{ext}"
    id_file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_name))

    cur = db.execute('''
        INSERT INTO applications
            (property_id, reference, full_name, email, phone, bio,
             employment, annual_income, move_in_date, id_type, id_filename,
             application_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_payment')
    ''', (
        property_id, reference,
        request.form['full_name'].strip(),
        request.form['email'].strip(),
        request.form['phone'].strip(),
        request.form['bio'].strip(),
        request.form['employment'].strip(),
        float(request.form.get('annual_income', 0) or 0),
        request.form.get('move_in_date', ''),
        request.form.get('id_type', 'Passport'),
        saved_name,
    ))
    db.commit()

    return jsonify({
        'reference': reference,
        'application_id': cur.lastrowid,
        'amount': PAYMENT_AMOUNT,
        'paypal_email': PAYPAL_EMAIL,
        'zelle_email': ZELLE_EMAIL,
        'zelle_phone': ZELLE_PHONE,
    }), 201


@app.route('/api/applications/<reference>/payment', methods=['POST'])
def api_record_payment(reference):
    data = request.get_json() or {}
    method = data.get('method')
    if method not in ('paypal', 'zelle'):
        return jsonify({'error': 'Method must be paypal or zelle'}), 400

    db = get_db()
    row = db.execute('SELECT * FROM applications WHERE reference = ?', (reference,)).fetchone()
    if not row:
        return jsonify({'error': 'Application not found'}), 404

    payment_ref = f"{method.upper()}-{uuid.uuid4().hex[:10].upper()}"
    db.execute('''
        UPDATE applications
        SET payment_method = ?, payment_status = 'paid',
            payment_reference = ?, application_status = 'submitted'
        WHERE reference = ?
    ''', (method, payment_ref, reference))
    db.commit()

    return jsonify({
        'success': True,
        'reference': reference,
        'payment_reference': payment_ref,
        'application_status': 'submitted',
    })


@app.route('/api/applications', methods=['GET'])
def api_list_applications():
    db = get_db()
    rows = db.execute('''
        SELECT a.*, p.title AS property_title, p.address AS property_address
        FROM applications a
        JOIN properties p ON p.id = a.property_id
        ORDER BY a.created_at DESC
    ''').fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/applications/<reference>', methods=['GET'])
def api_get_application(reference):
    db = get_db()
    row = db.execute('''
        SELECT a.*, p.title AS property_title, p.address AS property_address, p.price AS property_price
        FROM applications a
        JOIN properties p ON p.id = a.property_id
        WHERE a.reference = ?
    ''', (reference,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/favicon.ico')
def favicon_ico():
    return Response(
        FAVICON_SVG,
        mimetype='image/svg+xml',
        headers={'Cache-Control': 'public, max-age=86400'}
    )


# ============================================================
# PAGES
# ============================================================
LANDING_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sarah Anderson | Real Estate Agent</title>
__FAVICON__
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; }
body { background:#f0f2f5; color:#1a1a2e; line-height:1.6; }

/* NAV */
.nav { position:sticky; top:0; z-index:100; background:rgba(26,26,46,0.98);
  backdrop-filter:blur(10px); padding:15px 0; box-shadow:0 2px 20px rgba(0,0,0,0.15); }
.nav-inner { max-width:1200px; margin:0 auto; padding:0 25px;
  display:flex; justify-content:space-between; align-items:center; }
.nav-logo { color:white; font-size:1.3rem; font-weight:700; display:flex; align-items:center; gap:10px; }
.nav-logo span { background:#e94560; padding:3px 12px; border-radius:20px; font-size:0.7rem; }
.nav-links { display:flex; gap:25px; align-items:center; }
.nav-links a { color:rgba(255,255,255,0.85); text-decoration:none; font-weight:500; font-size:0.95rem; }
.nav-links a:hover { color:white; }
.nav-cta { background:#e94560; color:white !important; padding:10px 22px; border-radius:30px; font-weight:600 !important; }
.nav-cta:hover { background:#d63850; }

/* HERO */
.hero { background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
  color:white; padding:90px 25px 110px; position:relative; overflow:hidden; }
.hero::before { content:''; position:absolute; top:-50%; right:-10%;
  width:600px; height:600px;
  background:radial-gradient(circle, rgba(233,69,96,0.15) 0%, transparent 70%);
  border-radius:50%; }
.hero-inner { max-width:1200px; margin:0 auto; display:grid;
  grid-template-columns:1.2fr 1fr; gap:60px; align-items:center;
  position:relative; z-index:1; }
.hero-text h1 { font-size:3.2rem; line-height:1.15; margin-bottom:20px; font-weight:800; }
.hero-text h1 span { color:#e94560; }
.hero-text p { font-size:1.15rem; color:rgba(255,255,255,0.75); margin-bottom:35px; max-width:520px; }
.hero-badges { display:flex; gap:15px; flex-wrap:wrap; margin-bottom:40px; }
.hero-badge { background:rgba(255,255,255,0.08); padding:10px 18px; border-radius:30px;
  font-size:0.9rem; border:1px solid rgba(255,255,255,0.1); }
.hero-actions { display:flex; gap:15px; flex-wrap:wrap; }
.btn-hero { padding:16px 32px; border-radius:12px; font-size:1rem; font-weight:600;
  text-decoration:none; display:inline-flex; align-items:center; gap:10px;
  transition:0.3s; cursor:pointer; border:none; }
.btn-hero-primary { background:#e94560; color:white; box-shadow:0 8px 25px rgba(233,69,96,0.4); }
.btn-hero-primary:hover { background:#d63850; transform:translateY(-3px); }
.btn-hero-ghost { background:transparent; color:white; border:2px solid rgba(255,255,255,0.25); }
.btn-hero-ghost:hover { border-color:white; background:rgba(255,255,255,0.08); }

/* PROFILE CARD */
.profile-card { background:white; border-radius:24px; padding:35px;
  box-shadow:0 25px 60px rgba(0,0,0,0.3); text-align:center;
  max-width:380px; margin-left:auto; color:#1a1a2e; }
.profile-avatar { width:130px; height:130px; border-radius:50%;
  background:linear-gradient(135deg,#667eea,#764ba2);
  margin:0 auto 20px; display:flex; align-items:center; justify-content:center;
  font-size:3rem; color:white; font-weight:700;
  border:5px solid white; box-shadow:0 8px 25px rgba(102,126,234,0.4); }
.profile-card h2 { font-size:1.6rem; margin-bottom:4px; }
.profile-role { color:#e94560; font-weight:600; font-size:0.95rem; margin-bottom:20px; }
.profile-stats { display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;
  padding:20px 0; border-top:1px solid #eee; border-bottom:1px solid #eee; margin-bottom:20px; }
.profile-stat-value { font-size:1.4rem; font-weight:700; }
.profile-stat-label { font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; color:#888; }
.profile-contact { display:flex; flex-direction:column; gap:10px; }
.profile-contact a { display:flex; align-items:center; gap:10px; justify-content:center;
  padding:12px; border-radius:10px; text-decoration:none; font-weight:600; font-size:0.9rem; transition:0.2s; }
.pc-whatsapp { background:#25D366; color:white; }
.pc-whatsapp:hover { background:#1eb857; }
.pc-email { background:#f0f2f5; color:#1a1a2e; }
.pc-email:hover { background:#e2e5ea; }

/* SECTIONS */
.section { padding:80px 25px; }
.section-inner { max-width:1200px; margin:0 auto; }
.section-title { text-align:center; font-size:2.2rem; margin-bottom:15px; font-weight:700; }
.section-subtitle { text-align:center; color:#666; font-size:1.05rem; margin-bottom:55px;
  max-width:600px; margin-left:auto; margin-right:auto; }

/* SERVICES */
.services { background:white; }
.services-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:25px; }
.service-card { padding:35px 28px; border-radius:16px; background:#f8f9fb;
  border:1px solid #eef0f4; transition:0.3s; }
.service-card:hover { transform:translateY(-5px); box-shadow:0 15px 35px rgba(0,0,0,0.08); border-color:#e94560; }
.service-icon { width:55px; height:55px; border-radius:14px;
  background:linear-gradient(135deg,#e94560,#ff6b81);
  display:flex; align-items:center; justify-content:center;
  font-size:1.6rem; margin-bottom:20px; color:white; }
.service-card h3 { font-size:1.15rem; margin-bottom:10px; }
.service-card p { color:#666; font-size:0.93rem; }

/* LISTINGS */
.featured { background:#f0f2f5; }
.featured-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:25px; }
.property-card { background:white; border-radius:16px; overflow:hidden;
  box-shadow:0 4px 20px rgba(0,0,0,0.07); transition:0.3s; display:flex; flex-direction:column; }
.property-card:hover { transform:translateY(-5px); box-shadow:0 12px 30px rgba(0,0,0,0.12); }
.property-image { height:190px; background:linear-gradient(135deg,#667eea,#764ba2);
  display:flex; align-items:center; justify-content:center; font-size:4rem; position:relative; }
.property-status { position:absolute; top:15px; right:15px; padding:6px 16px;
  border-radius:20px; font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; }
.status-for-sale { background:#28a745; color:white; }
.status-for-rent { background:#17a2b8; color:white; }
.status-sold { background:#dc3545; color:white; }
.status-pending { background:#ffc107; color:#1a1a2e; }
.property-body { padding:22px; flex:1; display:flex; flex-direction:column; }
.property-price { font-size:1.5rem; font-weight:700; color:#e94560; margin-bottom:6px; }
.property-title { font-size:1.1rem; font-weight:600; margin-bottom:8px; }
.property-address { color:#666; font-size:0.9rem; margin-bottom:15px; }
.property-details { display:flex; gap:15px; padding:14px 0;
  border-top:1px solid #eee; border-bottom:1px solid #eee; margin-bottom:16px;
  font-size:0.85rem; color:#555; flex-wrap:wrap; }
.property-actions { display:flex; gap:10px; margin-top:auto; }
.btn-apply { flex:1; padding:12px; border:none; border-radius:10px;
  background:#e94560; color:white; font-weight:600; font-size:0.9rem;
  cursor:pointer; transition:0.2s; }
.btn-apply:hover { background:#d63850; transform:translateY(-2px); }

/* TESTIMONIALS */
.testimonials { background:white; }
.testi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:25px; }
.testi-card { background:#f8f9fb; padding:32px; border-radius:16px; border-left:4px solid #e94560; }
.testi-stars { color:#ffb400; margin-bottom:15px; letter-spacing:2px; }
.testi-text { color:#444; font-style:italic; margin-bottom:20px; line-height:1.7; }
.testi-author { display:flex; align-items:center; gap:12px; }
.testi-avatar { width:45px; height:45px; border-radius:50%;
  background:linear-gradient(135deg,#667eea,#764ba2);
  display:flex; align-items:center; justify-content:center; color:white; font-weight:700; }
.testi-name { font-weight:600; font-size:0.95rem; }
.testi-role { color:#888; font-size:0.82rem; }

/* CTA */
.cta-section { background:linear-gradient(135deg,#e94560,#c23152);
  color:white; padding:80px 25px; text-align:center; }
.cta-section h2 { font-size:2.4rem; margin-bottom:15px; }
.cta-section p { font-size:1.1rem; opacity:0.9; margin-bottom:35px; max-width:550px; margin-left:auto; margin-right:auto; }
.btn-cta { display:inline-flex; align-items:center; gap:10px;
  background:white; color:#e94560; padding:16px 36px; border-radius:12px;
  text-decoration:none; font-weight:700; font-size:1rem; transition:0.3s;
  box-shadow:0 8px 25px rgba(0,0,0,0.2); }
.btn-cta:hover { transform:translateY(-3px); box-shadow:0 12px 30px rgba(0,0,0,0.3); }

/* FOOTER */
footer { background:#1a1a2e; color:rgba(255,255,255,0.6);
  padding:40px 25px; text-align:center; font-size:0.9rem; }
footer a { color:#e94560; text-decoration:none; }

__WHATSAPP_CSS__

@media(max-width:900px){
  .hero-inner { grid-template-columns:1fr; text-align:center; }
  .hero-text h1 { font-size:2.3rem; }
  .hero-text p { margin-left:auto; margin-right:auto; }
  .hero-badges, .hero-actions { justify-content:center; }
  .profile-card { margin:40px auto 0; }
  .nav-links a:not(.nav-cta) { display:none; }
}
@media(max-width:500px){
  .hero-text h1 { font-size:1.9rem; }
  .section { padding:60px 20px; }
  .section-title { font-size:1.7rem; }
  .cta-section h2 { font-size:1.7rem; }
}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <div class="nav-logo">🏠 __AGENT_NAME__ <span>AGENT</span></div>
    <div class="nav-links">
      <a href="#services">Services</a>
      <a href="#featured">Listings</a>
      <a href="#testimonials">Reviews</a>
      
    </div>
  </div>
</nav>

<section class="hero">
  <div class="hero-inner">
    <div class="hero-text">
      <h1>Find Your <span>Dream Home</span> With A Trusted Local Expert</h1>
      <p>__AGENT_BIO__</p>
      <div class="hero-badges">
        <div class="hero-badge">⭐ 4.9/5 Rating</div>
        <div class="hero-badge">🏆 Top 1% Agent</div>
        <div class="hero-badge">📍 Licensed in NY, CA &amp; FL</div>
      </div>
      <div class="hero-actions">
        <a href="#featured" class="btn-hero btn-hero-primary">🏘️ Browse Listings</a>
        <a href="#contact" class="btn-hero btn-hero-ghost">💬 Get In Touch</a>
      </div>
    </div>

    <div class="profile-card">
      <div class="profile-avatar">SA</div>
      <h2>__AGENT_NAME__</h2>
      <div class="profile-role">__AGENT_TITLE__</div>
      <div class="profile-stats">
        <div><div class="profile-stat-value">__AGENT_YEARS__</div><div class="profile-stat-label">Years</div></div>
        <div><div class="profile-stat-value">__AGENT_SALES__</div><div class="profile-stat-label">Sales</div></div>
        <div><div class="profile-stat-value">__AGENT_VOLUME__</div><div class="profile-stat-label">Volume</div></div>
      </div>
      <div class="profile-contact">
        <a href="https://wa.me/__WHATSAPP_NUMBER__?text=__WHATSAPP_MSG__" target="_blank" class="pc-whatsapp">
          💬 Chat on WhatsApp
        </a>
        <a href="mailto:__AGENT_EMAIL__" class="pc-email">✉️ __AGENT_EMAIL__</a>
      </div>
    </div>
  </div>
</section>

<section class="section services" id="services">
  <div class="section-inner">
    <h2 class="section-title">How I Can Help</h2>
    <p class="section-subtitle">Full-service real estate support from first showing to final signature.</p>
    <div class="services-grid">
      <div class="service-card">
        <div class="service-icon">🏡</div>
        <h3>Buyer Representation</h3>
        <p>Personalized tours, market analysis, and expert negotiation to secure your ideal home at the right price.</p>
      </div>
      <div class="service-card">
        <div class="service-icon">📸</div>
        <h3>Listing &amp; Marketing</h3>
        <p>Professional photography, 3D tours, and multi-channel marketing that gets your property seen by serious buyers.</p>
      </div>
      <div class="service-card">
        <div class="service-icon">💼</div>
        <h3>Investment Advisory</h3>
        <p>Data-driven guidance on rental yields, cap rates, and off-market opportunities for your portfolio.</p>
      </div>
      <div class="service-card">
        <div class="service-icon">📝</div>
        <h3>Contract &amp; Closing</h3>
        <p>End-to-end paperwork, inspection coordination, and closing support so nothing falls through.</p>
      </div>
    </div>
  </div>
</section>

<section class="section featured" id="featured">
  <div class="section-inner">
    <h2 class="section-title">Featured Listings</h2>
    <p class="section-subtitle">Hand-picked properties currently on the market. Click Apply to start a $50 application.</p>
    <div class="featured-grid" id="featuredGrid">
      <div style="grid-column:1/-1;text-align:center;color:#888;">Loading listings…</div>
    </div>
  </div>
</section>

<section class="section testimonials" id="testimonials">
  <div class="section-inner">
    <h2 class="section-title">What Clients Say</h2>
    <p class="section-subtitle">Real stories from families I've helped.</p>
    <div class="testi-grid">
      <div class="testi-card">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Sarah found us our dream home in under three weeks. Her negotiation saved us $40K on the final price."</p>
        <div class="testi-author">
          <div class="testi-avatar">MJ</div>
          <div><div class="testi-name">Michael Johnson</div><div class="testi-role">First-time Buyer</div></div>
        </div>
      </div>
      <div class="testi-card">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Professional, responsive, and truly cared about finding the right fit for our family. Highly recommended."</p>
        <div class="testi-author">
          <div class="testi-avatar">EC</div>
          <div><div class="testi-name">Emily Chen</div><div class="testi-role">Relocated from Seattle</div></div>
        </div>
      </div>
      <div class="testi-card">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Sold our home above asking in 9 days. Sarah's marketing and staging advice made all the difference."</p>
        <div class="testi-author">
          <div class="testi-avatar">DR</div>
          <div><div class="testi-name">David Rodriguez</div><div class="testi-role">Home Seller</div></div>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="cta-section" id="contact">
  <h2>Ready to Find Your Next Home?</h2>
  <p>Let's talk about your goals. I'm available 7 days a week — via email, phone, or WhatsApp.</p>
  <a href="https://wa.me/__WHATSAPP_NUMBER__?text=__WHATSAPP_MSG__" target="_blank" class="btn-cta">💬 Message Me on WhatsApp</a>
</section>

<footer>
  &copy; 2025 __AGENT_NAME__ · __AGENT_TITLE__ ·
  <a href="mailto:__AGENT_EMAIL__">__AGENT_EMAIL__</a> ·
  
</footer>

__WHATSAPP_BUTTON__

<script>
async function loadFeatured() {
  try {
    const res = await fetch('/api/properties');
    const props = (await res.json()).filter(p => p.status === 'For Sale' || p.status === 'For Rent').slice(0, 6);
    const grid = document.getElementById('featuredGrid');
    if (!props.length) {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#888;">No listings available right now.</div>';
      return;
    }
    grid.innerHTML = props.map(p => {
      const statusClass = {
        'For Sale':'status-for-sale','For Rent':'status-for-rent',
        'Sold':'status-sold','Pending':'status-pending'
      }[p.status] || '';
      const emoji = {House:'🏡',Apartment:'🏢',Condo:'🏬',Townhouse:'🏘️',Land:'🌳'}[p.type] || '🏠';
      const price = p.status === 'For Rent'
        ? '$' + Number(p.price).toLocaleString() + '/mo'
        : '$' + Number(p.price).toLocaleString();
      return `
        <div class="property-card">
          <div class="property-image">
            <span>${emoji}</span>
            <div class="property-status ${statusClass}">${p.status}</div>
          </div>
          <div class="property-body">
            <div class="property-price">${price}</div>
            <div class="property-title">${escapeHtml(p.title)}</div>
            <div class="property-address">📍 ${escapeHtml(p.address)}</div>
            <div class="property-details">
              <span>🛏️ ${p.bedrooms} beds</span>
              <span>🛁 ${p.bathrooms} baths</span>
              <span>📐 ${Number(p.sqft).toLocaleString()} sqft</span>
            </div>
            <div class="property-actions">
              <button class="btn-apply" onclick="startApplication(${p.id})">📝 Apply ($50)</button>
            </div>
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    document.getElementById('featuredGrid').innerHTML =
      '<div style="grid-column:1/-1;text-align:center;color:#c00;">Failed to load listings.</div>';
  }
}
function escapeHtml(t){const d=document.createElement('div');d.textContent=t??'';return d.innerHTML;}
function startApplication(id){ window.location.href = '/apply/' + id; }
loadFeatured();
</script>
</body>
</html>
"""


MANAGE_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Property Manager — Sarah Anderson</title>
__FAVICON__
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; }
body { background:#f0f2f5; color:#1a1a2e; padding:20px; min-height:100vh; }
.container { max-width:1300px; margin:0 auto; }

.header { background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
  color:white; padding:25px 35px; border-radius:16px; margin-bottom:30px;
  display:flex; justify-content:space-between; align-items:center;
  flex-wrap:wrap; gap:15px; box-shadow:0 10px 30px rgba(0,0,0,0.15); }
.header h1 { font-size:1.8rem; display:flex; align-items:center; gap:12px; }
.header h1 span { background:#e94560; padding:4px 14px; border-radius:30px; font-size:0.8rem; font-weight:500; }
.header a { color:white; text-decoration:none; background:rgba(255,255,255,0.15);
  padding:10px 20px; border-radius:30px; font-weight:600; font-size:0.9rem; }
.header a:hover { background:rgba(255,255,255,0.25); }

.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:20px; margin-bottom:30px; }
.stat-card { background:white; padding:22px; border-radius:14px;
  box-shadow:0 4px 15px rgba(0,0,0,0.05); border-left:5px solid #e94560; }
.stat-card h3 { font-size:0.8rem; text-transform:uppercase; letter-spacing:1px; color:#666; margin-bottom:8px; }
.stat-card .value { font-size:1.8rem; font-weight:700; }

.controls { display:flex; justify-content:space-between; align-items:center;
  flex-wrap:wrap; gap:15px; margin-bottom:25px; }
.search-box { flex:1; min-width:250px; max-width:400px; position:relative; }
.search-box input { width:100%; padding:14px 20px 14px 45px;
  border:2px solid #e0e0e0; border-radius:12px; font-size:1rem; background:white; }
.search-box input:focus { outline:none; border-color:#e94560; }
.search-box::before { content:'🔍'; position:absolute; left:16px; top:50%; transform:translateY(-50%); }

.btn { padding:14px 28px; border:none; border-radius:12px; font-size:1rem;
  font-weight:600; cursor:pointer; transition:0.3s; display:inline-flex;
  align-items:center; gap:8px; text-decoration:none; }
.btn-primary { background:#e94560; color:white; box-shadow:0 4px 15px rgba(233,69,96,0.3); }
.btn-primary:hover { background:#d63850; transform:translateY(-2px); }
.btn-secondary { background:white; color:#1a1a2e; border:2px solid #e0e0e0; }
.btn-secondary:hover { border-color:#e94560; color:#e94560; }
.btn-danger { background:#dc3545; color:white; }
.btn-danger:hover { background:#c82333; }
.btn-sm { padding:8px 16px; font-size:0.85rem; }

.filter-tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }
.filter-tab { padding:10px 20px; border:2px solid #e0e0e0; background:white;
  border-radius:30px; cursor:pointer; font-weight:600; font-size:0.9rem; color:#666; }
.filter-tab:hover { border-color:#e94560; color:#e94560; }
.filter-tab.active { background:#e94560; border-color:#e94560; color:white; }

.property-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:25px; }
.property-card { background:white; border-radius:16px; overflow:hidden;
  box-shadow:0 4px 20px rgba(0,0,0,0.07); display:flex; flex-direction:column; }
.property-image { height:180px; background:linear-gradient(135deg,#667eea,#764ba2);
  display:flex; align-items:center; justify-content:center; font-size:4rem; position:relative; }
.property-status { position:absolute; top:15px; right:15px; padding:6px 16px;
  border-radius:20px; font-size:0.72rem; font-weight:700; text-transform:uppercase; }
.status-for-sale { background:#28a745; color:white; }
.status-for-rent { background:#17a2b8; color:white; }
.status-sold { background:#dc3545; color:white; }
.status-pending { background:#ffc107; color:#1a1a2e; }
.property-body { padding:22px; flex:1; display:flex; flex-direction:column; }
.property-price { font-size:1.5rem; font-weight:700; color:#e94560; margin-bottom:6px; }
.property-title { font-size:1.1rem; font-weight:600; margin-bottom:8px; }
.property-address { color:#666; font-size:0.9rem; margin-bottom:15px; }
.property-details { display:flex; gap:15px; padding:14px 0;
  border-top:1px solid #eee; border-bottom:1px solid #eee; margin-bottom:16px;
  font-size:0.85rem; color:#555; flex-wrap:wrap; }
.property-actions { display:flex; gap:10px; margin-top:auto; }
.property-actions .btn { flex:1; justify-content:center; }

.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6);
  backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center;
  z-index:1000; padding:20px; }
.modal-overlay.active { display:flex; }
.modal { background:white; border-radius:20px; width:100%; max-width:600px;
  max-height:90vh; overflow-y:auto; }
.modal-header { padding:25px 30px; border-bottom:1px solid #eee;
  display:flex; justify-content:space-between; align-items:center;
  position:sticky; top:0; background:white; }
.modal-header h2 { font-size:1.4rem; }
.modal-close { background:none; border:none; font-size:1.8rem; cursor:pointer; color:#999; }
.modal-close:hover { color:#e94560; }
.modal-body { padding:25px 30px; }
.modal-footer { padding:20px 30px 25px; display:flex; gap:12px; justify-content:flex-end; }

.form-group { margin-bottom:20px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
.form-group label { display:block; margin-bottom:7px; font-weight:600; font-size:0.9rem; }
.form-group input, .form-group select, .form-group textarea {
  width:100%; padding:12px 15px; border:2px solid #e0e0e0;
  border-radius:10px; font-size:0.95rem; font-family:inherit; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  outline:none; border-color:#e94560; }
.form-group textarea { resize:vertical; min-height:80px; }

.empty-state { text-align:center; padding:80px 20px; background:white;
  border-radius:16px; grid-column:1/-1; }
.empty-state .icon { font-size:5rem; margin-bottom:20px; }
.empty-state h3 { font-size:1.4rem; margin-bottom:10px; }
.empty-state p { color:#888; }

.toast { position:fixed; bottom:100px; right:30px; background:#1a1a2e; color:white;
  padding:16px 24px; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,0.2);
  display:flex; align-items:center; gap:12px; transform:translateX(400px);
  transition:0.4s; z-index:2000; font-weight:500; }
.toast.show { transform:translateX(0); }
.toast.success { border-left:5px solid #28a745; }
.toast.error { border-left:5px solid #dc3545; }

.applications-panel { background:white; border-radius:16px; padding:25px; margin-top:40px; }
.applications-panel h2 { font-size:1.4rem; margin-bottom:20px; }
.app-row { padding:15px; border-bottom:1px solid #eee; display:grid;
  grid-template-columns:1fr 1fr auto; gap:15px; align-items:center; }
.app-row:last-child { border-bottom:none; }
.app-ref { font-weight:700; color:#e94560; font-family:monospace; }
.app-meta { font-size:0.85rem; color:#666; }
.app-badge { padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:700; text-transform:uppercase; }
.badge-paid { background:#d4edda; color:#155724; }
.badge-pending { background:#fff3cd; color:#856404; }

__WHATSAPP_CSS__

@media(max-width:768px){
  .form-row { grid-template-columns:1fr; }
  .property-grid { grid-template-columns:1fr; }
  .app-row { grid-template-columns:1fr; }
}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <h1>🏠 Property Manager <span>AGENT</span></h1>
    <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
      <a href="/">← View Public Site</a>
      <div style="display:flex;align-items:center;gap:10px;background:rgba(255,255,255,0.1);
        padding:8px 16px;border-radius:50px;">
        <div style="width:38px;height:38px;background:#e94560;border-radius:50%;
          display:flex;align-items:center;justify-content:center;font-weight:bold;">SA</div>
        <div>
          <div style="font-weight:600;font-size:0.9rem;">Sarah Anderson</div>
          <div style="font-size:0.75rem;opacity:0.8;">Licensed Agent</div>
        </div>
      </div>
    </div>
  </header>

  <div class="stats">
    <div class="stat-card"><h3>Total Listings</h3><div class="value" id="totalCount">—</div></div>
    <div class="stat-card"><h3>For Sale</h3><div class="value" id="saleCount">—</div></div>
    <div class="stat-card"><h3>For Rent</h3><div class="value" id="rentCount">—</div></div>
    <div class="stat-card"><h3>Total Value</h3><div class="value" id="totalValue">—</div></div>
    <div class="stat-card"><h3>Applications</h3><div class="value" id="appCount">—</div></div>
  </div>

  <div class="controls">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="Search by address, city, or title...">
    </div>
    <button class="btn btn-primary" onclick="openModal()">➕ Add New Property</button>
  </div>

  <div class="filter-tabs">
    <button class="filter-tab active" data-filter="all" onclick="setFilter('all',this)">All Properties</button>
    <button class="filter-tab" data-filter="For Sale" onclick="setFilter('For Sale',this)">For Sale</button>
    <button class="filter-tab" data-filter="For Rent" onclick="setFilter('For Rent',this)">For Rent</button>
    <button class="filter-tab" data-filter="Sold" onclick="setFilter('Sold',this)">Sold</button>
    <button class="filter-tab" data-filter="Pending" onclick="setFilter('Pending',this)">Pending</button>
  </div>

  <div class="property-grid" id="propertyGrid">
    <div class="empty-state"><div class="icon">⏳</div><h3>Loading properties…</h3></div>
  </div>

  <div class="applications-panel">
    <h2>📋 Applications Received</h2>
    <div id="appList"><div style="color:#888;text-align:center;padding:20px;">Loading…</div></div>
  </div>
</div>

<div class="modal-overlay" id="modalOverlay">
  <div class="modal">
    <div class="modal-header">
      <h2 id="modalTitle">Add New Property</h2>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body">
      <form id="propertyForm">
        <input type="hidden" id="propertyId">
        <div class="form-group"><label>Title *</label>
          <input type="text" id="title" required></div>
        <div class="form-row">
          <div class="form-group"><label>Price ($) *</label>
            <input type="number" id="price" required min="0" step="1000"></div>
          <div class="form-group"><label>Status *</label>
            <select id="status" required>
              <option value="For Sale">For Sale</option>
              <option value="For Rent">For Rent</option>
              <option value="Pending">Pending</option>
              <option value="Sold">Sold</option>
            </select></div>
        </div>
        <div class="form-group"><label>Address *</label>
          <input type="text" id="address" required></div>
        <div class="form-row">
          <div class="form-group"><label>Bedrooms</label>
            <input type="number" id="bedrooms" min="0" value="3"></div>
          <div class="form-group"><label>Bathrooms</label>
            <input type="number" id="bathrooms" min="0" step="0.5" value="2"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Sqft</label>
            <input type="number" id="sqft" min="0"></div>
          <div class="form-group"><label>Type</label>
            <select id="type">
              <option>House</option><option>Apartment</option>
              <option>Condo</option><option>Townhouse</option><option>Land</option>
            </select></div>
        </div>
        <div class="form-group"><label>Description</label>
          <textarea id="description"></textarea></div>
      </form>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="saveProperty()">💾 Save Property</button>
    </div>
  </div>
</div>

<div class="toast" id="toast">
  <span id="toastIcon">✓</span><span id="toastMessage">Saved!</span>
</div>

__WHATSAPP_BUTTON__

<script>
let currentFilter = 'all';
let searchTerm = '';
let searchDebounce;

async function api(path, options = {}) {
  const res = await fetch(path, { headers: {'Content-Type':'application/json'}, ...options });
  if (!res.ok) {
    let msg = 'HTTP ' + res.status;
    try { msg = (await res.json()).error || msg; } catch(e){}
    throw new Error(msg);
  }
  return res.json();
}

async function loadProperties() {
  try {
    const params = new URLSearchParams();
    if (currentFilter !== 'all') params.set('status', currentFilter);
    if (searchTerm) params.set('search', searchTerm);
    const props = await api('/api/properties?' + params);
    renderProperties(props);
    await loadStats();
    await loadApplications();
  } catch (e) { showToast('Load failed: ' + e.message, 'error'); }
}

async function loadStats() {
  try {
    const s = await api('/api/stats');
    document.getElementById('totalCount').textContent = s.total;
    document.getElementById('saleCount').textContent = s.for_sale;
    document.getElementById('rentCount').textContent = s.for_rent;
    document.getElementById('totalValue').textContent = '$' + Number(s.total_value).toLocaleString();
    document.getElementById('appCount').textContent = s.applications;
  } catch(e){}
}

async function loadApplications() {
  try {
    const apps = await api('/api/applications');
    const list = document.getElementById('appList');
    if (!apps.length) {
      list.innerHTML = '<div style="color:#888;text-align:center;padding:20px;">No applications yet.</div>';
      return;
    }
    list.innerHTML = apps.map(a => `
      <div class="app-row">
        <div>
          <div class="app-ref">${a.reference}</div>
          <div class="app-meta">${escapeHtml(a.full_name)} · ${escapeHtml(a.email)}</div>
        </div>
        <div>
          <div style="font-weight:600;">${escapeHtml(a.property_title)}</div>
          <div class="app-meta">$${a.annual_income ? Number(a.annual_income).toLocaleString() : 0}/yr income</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span class="app-badge ${a.payment_status==='paid'?'badge-paid':'badge-pending'}">${a.payment_status}</span>
          <a href="/uploads/${a.id_filename}" target="_blank" class="btn btn-secondary btn-sm">🪪 ID</a>
        </div>
      </div>
    `).join('');
  } catch(e){}
}

function escapeHtml(t){const d=document.createElement('div');d.textContent=t??'';return d.innerHTML;}

function renderProperties(props) {
  const grid = document.getElementById('propertyGrid');
  if (!props.length) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">🏘️</div><h3>No properties found</h3><p>Add your first listing or adjust filters.</p></div>';
    return;
  }
  grid.innerHTML = props.map(p => {
    const sc = {'For Sale':'status-for-sale','For Rent':'status-for-rent',
      'Sold':'status-sold','Pending':'status-pending'}[p.status] || '';
    const em = {House:'🏡',Apartment:'🏢',Condo:'🏬',Townhouse:'🏘️',Land:'🌳'}[p.type] || '🏠';
    const price = p.status === 'For Rent'
      ? '$' + Number(p.price).toLocaleString() + '/mo'
      : '$' + Number(p.price).toLocaleString();
    return `
      <div class="property-card">
        <div class="property-image">
          <span>${em}</span><div class="property-status ${sc}">${p.status}</div>
        </div>
        <div class="property-body">
          <div class="property-price">${price}</div>
          <div class="property-title">${escapeHtml(p.title)}</div>
          <div class="property-address">📍 ${escapeHtml(p.address)}</div>
          <div class="property-details">
            <span>🛏️ ${p.bedrooms}</span><span>🛁 ${p.bathrooms}</span>
            <span>📐 ${Number(p.sqft).toLocaleString()}</span>
          </div>
          <div class="property-actions">
            <button class="btn btn-secondary btn-sm" onclick="editProperty(${p.id})">✏️ Edit</button>
            <button class="btn btn-danger btn-sm" onclick="deleteProperty(${p.id})">🗑️ Delete</button>
          </div>
        </div>
      </div>`;
  }).join('');
}

function openModal(property = null) {
  document.getElementById('propertyForm').reset();
  if (property) {
    document.getElementById('modalTitle').textContent = 'Edit Property';
    document.getElementById('propertyId').value = property.id;
    ['title','price','status','address','bedrooms','bathrooms','sqft','type','description']
      .forEach(k => document.getElementById(k).value = property[k] ?? '');
  } else {
    document.getElementById('modalTitle').textContent = 'Add New Property';
    document.getElementById('propertyId').value = '';
  }
  document.getElementById('modalOverlay').classList.add('active');
}
function closeModal() { document.getElementById('modalOverlay').classList.remove('active'); }

async function editProperty(id) {
  try { openModal(await api('/api/properties/' + id)); }
  catch(e){ showToast('Load failed: ' + e.message, 'error'); }
}

async function saveProperty() {
  const form = document.getElementById('propertyForm');
  if (!form.checkValidity()) { form.reportValidity(); return; }
  const id = document.getElementById('propertyId').value;
  const payload = {
    title: document.getElementById('title').value.trim(),
    price: Number(document.getElementById('price').value),
    status: document.getElementById('status').value,
    address: document.getElementById('address').value.trim(),
    bedrooms: Number(document.getElementById('bedrooms').value) || 0,
    bathrooms: Number(document.getElementById('bathrooms').value) || 0,
    sqft: Number(document.getElementById('sqft').value) || 0,
    type: document.getElementById('type').value,
    description: document.getElementById('description').value.trim()
  };
  try {
    if (id) {
      await api('/api/properties/' + id, {method:'PUT', body: JSON.stringify(payload)});
      showToast('Property updated!', 'success');
    } else {
      await api('/api/properties', {method:'POST', body: JSON.stringify(payload)});
      showToast('Property added!', 'success');
    }
    closeModal();
    await loadProperties();
  } catch(e){ showToast('Save failed: ' + e.message, 'error'); }
}

async function deleteProperty(id) {
  if (!confirm('Delete this listing and its applications?')) return;
  try {
    await api('/api/properties/' + id, {method:'DELETE'});
    showToast('Property deleted.', 'error');
    await loadProperties();
  } catch(e){ showToast('Delete failed: ' + e.message, 'error'); }
}

function setFilter(f, btn) {
  currentFilter = f;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  loadProperties();
}

document.getElementById('searchInput').addEventListener('input', e => {
  searchTerm = e.target.value;
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadProperties, 300);
});

document.getElementById('modalOverlay').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

let toastTimeout;
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  document.getElementById('toastIcon').textContent = type === 'success' ? '✓' : '⚠️';
  document.getElementById('toastMessage').textContent = msg;
  t.className = 'toast ' + type;
  t.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => t.classList.remove('show'), 3000);
}

loadProperties();
</script>
</body>
</html>
"""


APPLY_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Apply — __PROPERTY_TITLE__</title>
__FAVICON__
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; }
body { background:#f0f2f5; color:#1a1a2e; padding:20px; min-height:100vh; }
.container { max-width:720px; margin:0 auto; }

.topbar { background:#1a1a2e; color:white; padding:16px 24px;
  border-radius:12px; display:flex; justify-content:space-between;
  align-items:center; margin-bottom:24px; }
.topbar a { color:white; text-decoration:none; opacity:0.85; font-size:0.9rem; }
.topbar a:hover { opacity:1; }

.card { background:white; border-radius:16px; padding:32px;
  box-shadow:0 4px 20px rgba(0,0,0,0.07); margin-bottom:24px; }
.card h2 { font-size:1.5rem; margin-bottom:8px; }
.card .subtitle { color:#666; margin-bottom:24px; font-size:0.95rem; }

.prop-summary { background:#f8f9fb; border-radius:12px; padding:18px;
  display:flex; justify-content:space-between; align-items:center;
  margin-bottom:24px; border-left:4px solid #e94560; }
.prop-summary h3 { font-size:1.1rem; margin-bottom:4px; }
.prop-summary p { color:#666; font-size:0.88rem; }
.prop-summary .price { font-size:1.4rem; color:#e94560; font-weight:700; }

.form-group { margin-bottom:20px; }
.form-row { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
.form-group label { display:block; margin-bottom:7px; font-weight:600; font-size:0.9rem; }
.form-group input, .form-group select, .form-group textarea {
  width:100%; padding:12px 15px; border:2px solid #e0e0e0;
  border-radius:10px; font-size:0.95rem; font-family:inherit; transition:0.2s; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  outline:none; border-color:#e94560; box-shadow:0 0 0 3px rgba(233,69,96,0.1); }
.form-group textarea { resize:vertical; min-height:90px; }
.form-group small { color:#888; font-size:0.8rem; display:block; margin-top:5px; }

.id-upload { border:2px dashed #ccc; border-radius:12px; padding:30px;
  text-align:center; cursor:pointer; transition:0.2s; }
.id-upload:hover, .id-upload.dragover { border-color:#e94560; background:#fef5f7; }
.id-upload input { display:none; }
.id-upload .icon { font-size:2.5rem; margin-bottom:10px; }
.id-upload .label { font-weight:600; margin-bottom:5px; }
.id-upload .hint { color:#888; font-size:0.85rem; }
.id-upload .filename { margin-top:10px; color:#e94560; font-weight:600; font-size:0.9rem; }

.btn { padding:14px 28px; border:none; border-radius:12px;
  font-size:1rem; font-weight:600; cursor:pointer; transition:0.3s;
  display:inline-flex; align-items:center; gap:8px; text-decoration:none; }
.btn-primary { background:#e94560; color:white; box-shadow:0 4px 15px rgba(233,69,96,0.3); }
.btn-primary:hover { background:#d63850; transform:translateY(-2px); }
.btn-primary:disabled { background:#ccc; cursor:not-allowed; transform:none; }
.btn-block { width:100%; justify-content:center; }

.payment-box { background:#fff8e1; border:2px solid #ffc107; border-radius:12px;
  padding:20px; margin-bottom:24px; }
.payment-box h3 { color:#856404; margin-bottom:8px; }
.payment-box p { color:#856404; font-size:0.9rem; margin-bottom:15px; }

.pay-methods { display:grid; grid-template-columns:1fr 1fr; gap:15px; }
.pay-method { padding:20px; border:2px solid #e0e0e0; border-radius:12px;
  cursor:pointer; text-align:center; transition:0.2s; background:white; }
.pay-method:hover { border-color:#e94560; }
.pay-method.selected { border-color:#e94560; background:#fef5f7; }
.pay-method .logo { font-size:2rem; margin-bottom:8px; }
.pay-method .name { font-weight:700; font-size:1rem; }
.pay-method .detail { color:#666; font-size:0.8rem; margin-top:4px; }

.step { display:none; }
.step.active { display:block; }
.step-indicator { display:flex; justify-content:center; gap:30px; margin-bottom:30px; }
.step-dot { display:flex; flex-direction:column; align-items:center; gap:6px; }
.step-dot .circle { width:36px; height:36px; border-radius:50%;
  background:#e0e0e0; color:#888; display:flex; align-items:center;
  justify-content:center; font-weight:700; }
.step-dot.active .circle { background:#e94560; color:white; }
.step-dot.done .circle { background:#28a745; color:white; }
.step-dot .lbl { font-size:0.8rem; color:#888; }
.step-dot.active .lbl { color:#e94560; font-weight:600; }

.success-box { text-align:center; padding:40px 20px; }
.success-box .check { font-size:5rem; color:#28a745; margin-bottom:20px; }
.success-box h2 { color:#1a1a2e; margin-bottom:10px; }
.success-box p { color:#666; margin-bottom:20px; }
.success-box .ref { background:#f0f2f5; padding:14px 24px; border-radius:10px;
  font-family:monospace; font-size:1.2rem; font-weight:700; color:#e94560;
  display:inline-block; margin-bottom:20px; }

__WHATSAPP_CSS__
@media(max-width:600px){
  .form-row, .pay-methods { grid-template-columns:1fr; }
}
</style>
</head>
<body>
<div class="container">

  <div class="topbar">
    <div><strong>🏠 Sarah Anderson Realty</strong></div>
    <a href="/">← Back to listings</a>
  </div>

  <div class="step-indicator">
    <div class="step-dot active" id="dot1"><div class="circle">1</div><div class="lbl">Details</div></div>
    <div class="step-dot" id="dot2"><div class="circle">2</div><div class="lbl">Payment</div></div>
    <div class="step-dot" id="dot3"><div class="circle">3</div><div class="lbl">Done</div></div>
  </div>

  <!-- STEP 1: DETAILS -->
  <div class="step active" id="step1">
    <div class="card">
      <h2>Property Application</h2>
      <p class="subtitle">Please provide your details. A $50 processing fee applies at the next step.</p>

      <div class="prop-summary">
        <div>
          <h3>__PROPERTY_TITLE__</h3>
          <p>📍 __PROPERTY_ADDRESS__</p>
        </div>
        <div class="price">__PROPERTY_PRICE__</div>
      </div>

      <form id="appForm">
        <input type="hidden" id="property_id" value="__PROPERTY_ID__">

        <div class="form-row">
          <div class="form-group">
            <label>Full Name *</label>
            <input type="text" id="full_name" required placeholder="John Doe">
          </div>
          <div class="form-group">
            <label>Email *</label>
            <input type="email" id="email" required placeholder="john@example.com">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Phone *</label>
            <input type="tel" id="phone" required placeholder="(555) 123-4567">
          </div>
          <div class="form-group">
            <label>Employment *</label>
            <input type="text" id="employment" required placeholder="e.g., Software Engineer at Acme">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Annual Income ($)</label>
            <input type="number" id="annual_income" min="0" step="1000" placeholder="80000">
          </div>
          <div class="form-group">
            <label>Desired Move-in Date</label>
            <input type="date" id="move_in_date">
          </div>
        </div>

        <div class="form-group">
          <label>Tell us about yourself (bio) *</label>
          <textarea id="bio" required placeholder="Share a short bio — occupation, family situation, why you're interested..."></textarea>
        </div>

        <div class="form-group">
          <label>ID Document *</label>
          <div class="id-upload" id="idDrop">
            <input type="file" id="id_file" accept=".jpg,.jpeg,.png,.pdf" required>
            <div class="icon">🪪</div>
            <div class="label">Click or drop your ID here</div>
            <div class="hint">Passport, Driver's License or National ID · JPG/PNG/PDF · Max 5MB</div>
            <div class="filename" id="idFilename"></div>
          </div>
        </div>

        <div class="form-group">
          <label>ID Type</label>
          <select id="id_type">
            <option value="Passport">Passport</option>
            <option value="Driver's License">Driver's License</option>
            <option value="National ID">National ID</option>
            <option value="Other">Other</option>
          </select>
        </div>

        <button type="button" class="btn btn-primary btn-block" onclick="submitDetails(event)">
          Continue to Payment →
        </button>
      </form>
    </div>
  </div>

  <!-- STEP 2: PAYMENT -->
  <div class="step" id="step2">
    <div class="card">
      <h2>Pay Application Fee</h2>
      <p class="subtitle">A $50.00 non-refundable processing fee is required to submit your application.</p>

      <div class="payment-box">
        <h3>💳 Amount Due: $50.00</h3>
        <p>Choose Zelle or PayPal to complete your application. You'll receive a confirmation reference.</p>

        <div class="pay-methods">
          <div class="pay-method" data-method="zelle" onclick="selectMethod('zelle', this)">
            <div class="logo">💵</div>
            <div class="name">Zelle</div>
            <div class="detail" id="zelleDetail">Loading…</div>
          </div>
          <div class="pay-method" data-method="paypal" onclick="selectMethod('paypal', this)">
            <div class="logo">💠</div>
            <div class="name">PayPal</div>
            <div class="detail" id="paypalDetail">Loading…</div>
          </div>
        </div>
      </div>

      <div id="paymentInstructions" style="display:none;background:#f8f9fb;border-radius:10px;
        padding:18px;margin-bottom:20px;font-size:0.9rem;"></div>

      <button class="btn btn-primary btn-block" id="payBtn" onclick="confirmPayment()" disabled>
        ✓ I've Paid $50 — Submit Application
      </button>

      <p style="text-align:center;margin-top:15px;font-size:0.8rem;color:#888;">
        This is a demo. In production, payments would be verified via webhook.
      </p>
    </div>
  </div>

  <!-- STEP 3: SUCCESS -->
  <div class="step" id="step3">
    <div class="card success-box">
      <div class="check">✅</div>
      <h2>Application Submitted!</h2>
      <p>Thank you! Your application has been received and is under review.</p>
      <div class="ref" id="finalRef">—</div>
      <p style="font-size:0.9rem;">Save this reference — the agent will contact you within 24 hours.</p>
      <a href="/" class="btn btn-primary" style="margin-top:20px;">← Back to Listings</a>
    </div>
  </div>

</div>

__WHATSAPP_BUTTON__

<script>
let paymentInfo = null;
let selectedMethod = null;
let currentReference = null;

const idDrop = document.getElementById('idDrop');
const idFile = document.getElementById('id_file');
idDrop.addEventListener('click', () => idFile.click());
idDrop.addEventListener('dragover', e => { e.preventDefault(); idDrop.classList.add('dragover'); });
idDrop.addEventListener('dragleave', () => idDrop.classList.remove('dragover'));
idDrop.addEventListener('drop', e => {
  e.preventDefault(); idDrop.classList.remove('dragover');
  if (e.dataTransfer.files.length) {
    idFile.files = e.dataTransfer.files;
    document.getElementById('idFilename').textContent = '📎 ' + e.dataTransfer.files[0].name;
  }
});
idFile.addEventListener('change', () => {
  document.getElementById('idFilename').textContent =
    idFile.files.length ? '📎 ' + idFile.files[0].name : '';
});

async function submitDetails(evt) {
  const form = document.getElementById('appForm');
  if (!form.checkValidity()) { form.reportValidity(); return; }
  if (!idFile.files.length) {
    alert('Please upload your ID document.');
    return;
  }

  const fd = new FormData();
  fd.append('property_id', document.getElementById('property_id').value);
  fd.append('full_name', document.getElementById('full_name').value);
  fd.append('email', document.getElementById('email').value);
  fd.append('phone', document.getElementById('phone').value);
  fd.append('employment', document.getElementById('employment').value);
  fd.append('annual_income', document.getElementById('annual_income').value);
  fd.append('move_in_date', document.getElementById('move_in_date').value);
  fd.append('bio', document.getElementById('bio').value);
  fd.append('id_type', document.getElementById('id_type').value);
  fd.append('id_file', idFile.files[0]);

  const btn = evt.target;
  btn.disabled = true;
  btn.textContent = 'Submitting…';

  try {
    const res = await fetch('/api/applications', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to submit');

    paymentInfo = data;
    currentReference = data.reference;

    document.getElementById('zelleDetail').textContent = data.zelle_email || data.zelle_phone;
    document.getElementById('paypalDetail').textContent = data.paypal_email;

    document.getElementById('step1').classList.remove('active');
    document.getElementById('step2').classList.add('active');
    document.getElementById('dot1').classList.add('done');
    document.getElementById('dot2').classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (e) {
    alert('Error: ' + e.message);
    btn.disabled = false;
    btn.textContent = 'Continue to Payment →';
  }
}

function selectMethod(method, el) {
  selectedMethod = method;
  document.querySelectorAll('.pay-method').forEach(m => m.classList.remove('selected'));
  el.classList.add('selected');

  const info = document.getElementById('paymentInstructions');
  const p = paymentInfo;
  if (method === 'zelle') {
    info.innerHTML = `
      <strong>📤 Send $${p.amount.toFixed(2)} via Zelle to:</strong><br>
      Email: <strong>${p.zelle_email}</strong><br>
      Phone: <strong>${p.zelle_phone}</strong><br>
      <br>
      <em>Include reference <strong>${p.reference}</strong> in the memo.</em>`;
  } else {
    info.innerHTML = `
      <strong>📤 Send $${p.amount.toFixed(2)} via PayPal to:</strong><br>
      Email: <strong>${p.paypal_email}</strong><br>
      <br>
      <em>Use "Send to a friend" and include reference <strong>${p.reference}</strong> in the note.</em>`;
  }
  info.style.display = 'block';
  document.getElementById('payBtn').disabled = false;
}

async function confirmPayment() {
  if (!selectedMethod) return;
  const btn = document.getElementById('payBtn');
  btn.disabled = true;
  btn.textContent = 'Verifying…';

  try {
    const res = await fetch(`/api/applications/${currentReference}/payment`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ method: selectedMethod })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Payment failed');

    document.getElementById('finalRef').textContent = currentReference;
    document.getElementById('step2').classList.remove('active');
    document.getElementById('step3').classList.add('active');
    document.getElementById('dot2').classList.remove('active');
    document.getElementById('dot2').classList.add('done');
    document.getElementById('dot3').classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (e) {
    alert('Error: ' + e.message);
    btn.disabled = false;
    btn.textContent = '✓ I\'ve Paid $50 — Submit Application';
  }
}
</script>
</body>
</html>
"""


# ============================================================
# PAGE ROUTES
# ============================================================
@app.route('/')
def landing():
    html = (LANDING_HTML
            .replace('__FAVICON__', FAVICON_TAG)
            .replace('__WHATSAPP_CSS__', WHATSAPP_CSS)
            .replace('__WHATSAPP_BUTTON__', whatsapp_button_html())
            .replace('__WHATSAPP_NUMBER__', WHATSAPP_NUMBER)
            .replace('__WHATSAPP_MSG__', quote(WHATSAPP_MESSAGE))
            .replace('__AGENT_NAME__', AGENT_NAME)
            .replace('__AGENT_TITLE__', AGENT_TITLE)
            .replace('__AGENT_EMAIL__', AGENT_EMAIL)
            .replace('__AGENT_BIO__', AGENT_BIO)
            .replace('__AGENT_YEARS__', AGENT_YEARS)
            .replace('__AGENT_SALES__', AGENT_SALES)
            .replace('__AGENT_VOLUME__', AGENT_VOLUME))
    return render_template_string(html)


@app.route('/manage')
def manage():
    html = (MANAGE_HTML
            .replace('__FAVICON__', FAVICON_TAG)
            .replace('__WHATSAPP_CSS__', WHATSAPP_CSS)
            .replace('__WHATSAPP_BUTTON__', whatsapp_button_html()))
    return render_template_string(html)


@app.route('/apply/<int:property_id>')
def apply_page(property_id):
    db = get_db()
    prop = db.execute('SELECT * FROM properties WHERE id = ?', (property_id,)).fetchone()
    if not prop:
        return "Property not found", 404

    price = (f"${prop['price']:,.0f}/mo" if prop['status'] == 'For Rent'
             else f"${prop['price']:,.0f}")

    html = (APPLY_HTML
            .replace('__FAVICON__', FAVICON_TAG)
            .replace('__WHATSAPP_CSS__', WHATSAPP_CSS)
            .replace('__WHATSAPP_BUTTON__', whatsapp_button_html())
            .replace('__PROPERTY_ID__', str(prop['id']))
            .replace('__PROPERTY_TITLE__', prop['title'])
            .replace('__PROPERTY_ADDRESS__', prop['address'])
            .replace('__PROPERTY_PRICE__', price))
    return render_template_string(html)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("  Real Estate Agent — Landing + Manager + Applications")
    print("  Landing  : http://localhost:5000/")
    print("  Manager  : http://localhost:5000/manage")
    print("  Uploads  : " + UPLOAD_DIR)
    print("  Favicon  : embedded SVG (no file needed)")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
