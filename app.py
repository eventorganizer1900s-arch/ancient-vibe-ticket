import io, os, secrets, sqlite3, zipfile
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template_string, send_file, abort
import qrcode

app = Flask(__name__)
DB = os.getenv('DB_PATH', 'tickets.db')
PIN = os.getenv('ADMIN_PIN', 'CHANGE-ME')
BASE_URL = os.getenv('BASE_URL', '').rstrip('/')

def connect():
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def init():
    os.makedirs(os.path.dirname(DB) or '.', exist_ok=True)
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS tickets (code TEXT UNIQUE, token TEXT UNIQUE, used INTEGER DEFAULT 0, checked_at TEXT)')
        n = c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
        while n < 1000:
            code = f'AV{n+1:04d}'
            try:
                c.execute('INSERT INTO tickets(code,token) VALUES (?,?)', (code, secrets.token_urlsafe(32)))
                n += 1
            except sqlite3.IntegrityError:
                pass

@app.get('/')
def home():
    return render_template_string('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#090909;color:#eee;font:18px Arial;max-width:550px;margin:30px auto;padding:18px}h1{color:#d8aa43}input,button{box-sizing:border-box;width:100%;padding:13px;margin:7px 0;border-radius:8px}button{background:#d8aa43;font-weight:bold}</style><h1>ANCIENT VIBE</h1><p>Secure event check-in</p><p>Scan the guest's QR ticket, then enter the token from its URL below.</p><input id="p" type="password" placeholder="Staff PIN"><input id="s" placeholder="Staff name"><input id="t" placeholder="Ticket token"><button onclick="go()">VERIFY & CHECK IN</button><h3 id="r"></h3><script>async function go(){let x=await fetch('/checkin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:p.value,staff:s.value,token:t.value})});let d=await x.json();r.textContent=d.message;r.style.color=d.ok?'#65e89a':'#ff7777'}</script>''')

@app.get('/ticket/<token>')
def ticket(token):
    with connect() as c:
        row = c.execute('SELECT code FROM tickets WHERE token=?', (token,)).fetchone()
    if not row: return 'INVALID TICKET', 404
    return f'''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><body style="background:#090909;color:#d8aa43;font:24px Arial;padding:25px"><h1>ANCIENT VIBE</h1><h2>EVENT TICKET</h2><p>{row['code']}</p><p>Show this ticket to staff at the entrance.</p></body>'''

@app.get('/admin/qr-codes')
def admin_page():
    return '''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font:18px Arial;max-width:500px;margin:30px auto;padding:18px"><h2>Ancient Vibe — Export 1,000 QR tickets</h2><p>Enter your private ADMIN_PIN to download a ZIP of the 1,000 ticket QR images. Keep the ZIP private.</p><form method="post"><input type="password" name="pin" placeholder="Admin PIN" required style="padding:12px;width:95%"><p><button style="padding:12px">Download QR ZIP</button></p></form></body>'''

@app.post('/admin/qr-codes')
def export_qr():
    if not secrets.compare_digest(request.form.get('pin',''), PIN):
        return 'Incorrect admin PIN', 401
    if not BASE_URL.startswith('https://'):
        return 'Set BASE_URL to your final public HTTPS website URL in Render environment variables, then try again.', 400
    memory = io.BytesIO()
    with connect() as c, zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED) as zf:
        rows = c.execute('SELECT code,token FROM tickets ORDER BY code').fetchall()
        if len(rows) != 1000:
            return f'Expected 1000 tickets, found {len(rows)}. Contact your administrator.', 500
        for row in rows:
            url = f"{BASE_URL}/ticket/{row['token']}"
            qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
            qr.add_data(url); qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            out = io.BytesIO(); img.save(out, format='PNG')
            zf.writestr(f"AncientVibe_{row['code']}.png", out.getvalue())
        zf.writestr('README.txt', 'Ancient Vibe ticket QR codes. Keep this ZIP private. Each QR contains a secret ticket link. Do not publish or share the full archive publicly. Test tickets before event day.')
    memory.seek(0)
    return send_file(memory, mimetype='application/zip', as_attachment=True, download_name='Ancient_Vibe_1000_QR_Tickets.zip')

@app.post('/checkin')
def checkin():
    d = request.get_json(silent=True) or {}
    if not secrets.compare_digest(str(d.get('pin','')), PIN):
        return jsonify(ok=False, message='Incorrect staff PIN'), 401
    token = str(d.get('token','')).strip()
    with connect() as c:
        row = c.execute('SELECT code,used FROM tickets WHERE token=?', (token,)).fetchone()
        if not row: return jsonify(ok=False, message='INVALID TICKET')
        if row['used']: return jsonify(ok=False, message='ALREADY USED — duplicate entry rejected')
        now = datetime.now(timezone.utc).isoformat()
        cur = c.execute('UPDATE tickets SET used=1,checked_at=? WHERE token=? AND used=0', (now, token))
        if cur.rowcount != 1: return jsonify(ok=False, message='ALREADY USED — duplicate entry rejected')
        return jsonify(ok=True, message=f"VALID — {row['code']} checked in")

init()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT','5000')))
