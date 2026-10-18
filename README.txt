ANCIENT VIBE — QR TICKET APP

This app creates 1,000 unique tickets in SQLite and exports one QR PNG per ticket.

GITHUB files: app.py, requirements.txt, README.txt only. Do NOT upload ticket_tokens_PRIVATE.csv or any secret/token export.

RENDER settings:
- Runtime: Python
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Environment variables:
  ADMIN_PIN = a strong private PIN (not CHANGE-ME)
  BASE_URL = https://YOUR-EXACT-RENDER-SERVICE.onrender.com
  DB_PATH = /var/data/tickets.db
- Attach a persistent disk mounted at /var/data before creating real tickets. Without persistent storage, SQLite data can be lost on service restart/redeploy. If your Render plan does not support persistent disks, use a persistent database such as PostgreSQL instead.

USAGE:
1. Visit /admin/qr-codes and enter ADMIN_PIN to download Ancient_Vibe_1000_QR_Tickets.zip.
2. Keep that ZIP private; each QR contains a secret ticket link.
3. Test a ticket, then check it in at / using staff PIN and the token portion of the URL.
4. Attempting to check the same ticket in again must return ALREADY USED.

IMPORTANT LIMITATIONS:
- This starter uses manual token entry at check-in; camera scanning is not implemented.
- Do not sell or distribute tickets until persistence, access controls, backups, HTTPS, and check-in have been tested on phones.
- Set BASE_URL to the exact final Render URL before generating QR codes. If the URL changes, generate a new batch before distributing tickets.
