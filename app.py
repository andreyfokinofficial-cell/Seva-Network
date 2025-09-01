from flask import Flask, render_template, request, redirect, url_for, g, flash, session, jsonify
import os, sys, hmac, hashlib, time, threading, sqlite3

# ---- Config
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "seva.db"))
DATABASE_URL = os.environ.get("DATABASE_URL")  # postgres://... or postgresql://...
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-key")

# ---- i18n (RU minimal)
def t(key):
    return {
        "app_title":"Seva Network",
        "people":"Участники",
        "create_profile":"Создать профиль",
        "hello":"Привет",
        "login":"Войти через Telegram",
        "logout":"Выйти",
        "reinit":"(Re)Init DB",
        "find":"Найти",
        "query":"Имя / навыки / о себе",
        "back_to_people":"Назад к участникам",
        "contacts":"Контакты",
    }.get(key, key)

@app.context_processor
def inject_globals():
    return dict(t=t, tg=session.get('tg'), bot_username=TELEGRAM_BOT_USERNAME)

# ---- DB layer (supports Postgres and SQLite)
_db_local = threading.local()

def is_postgres():
    return bool(DATABASE_URL)

def get_db():
    conn = getattr(_db_local, "conn", None)
    if conn is not None:
        return conn
    if is_postgres():
        import psycopg2, psycopg2.extras
        dsn = DATABASE_URL
        if "sslmode=" not in dsn:
            dsn = dsn + ("&" if "?" in dsn else "?") + "sslmode=require"
        conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
        _db_local.conn = conn
        return conn
    # SQLite
    db_path = DATABASE_PATH
    if db_path.startswith("/opt/render/project/src"):
        db_path = "/tmp/seva.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _db_local.conn = conn
    return conn

@app.teardown_appcontext
def close_connection(_):
    conn = getattr(_db_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        finally:
            _db_local.conn = None

def execute(sql, params=()):
    conn = get_db()
    cur = conn.cursor()
    if is_postgres():
        sql = sql.replace("?", "%s")
    cur.execute(sql, params)
    return cur

def commit():
    get_db().commit()

def insert_and_get_id(sql, params=()):
    if is_postgres():
        sql = sql.replace("?", "%s")
        if "returning id" not in sql.lower():
            sql = sql.rstrip() + " RETURNING id"
        cur = execute(sql, params)
        rid = cur.fetchone()["id"]
        commit()
        return rid
    else:
        cur = execute(sql, params)
        rid = cur.lastrowid
        commit()
        return rid

def init_db():
    conn = get_db()
    cur = conn.cursor()
    if is_postgres():
        with open(os.path.join(os.path.dirname(__file__), "schema_postgres.sql"), "r", encoding="utf-8") as f:
            cur.execute(f.read())
        cur.executemany("INSERT INTO service_tags (name, category) VALUES (%s,%s)", [
            ("дизайн","creative"),("перевод","language"),("медиа","media")
        ])
    else:
        with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r", encoding="utf-8") as f:
            cur.executescript(f.read())
        cur.executemany("INSERT INTO service_tags (name, category) VALUES (?,?)", [
            ("дизайн","creative"),("перевод","language"),("медиа","media")
        ])
    conn.commit()

# ---- Health
@app.route("/health")
def health():
    try:
        execute("SELECT 1")
        return jsonify(status="ok"), 200
    except Exception as e:
        return jsonify(status="error", detail=str(e)), 500

# ---- Telegram login verify
def verify_telegram_auth(data: dict) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        return False
    check_hash = data.get("hash")
    auth = dict(data)
    auth.pop("hash", None)
    pairs = [f"{k}={auth[k]}" for k in sorted(auth.keys())]
    s = "\n".join(pairs)
    secret = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    h = hmac.new(secret, s.encode(), hashlib.sha256).hexdigest()
    if h != check_hash:
        return False
    ts = int(auth.get("auth_date", "0") or 0)
    if ts and (time.time() - ts) > 86400:
        return False
    return True

@app.route("/auth/telegram", methods=["GET","POST"])
def auth_telegram():
    data = request.values.to_dict()
    if not data:
        flash("Нет данных авторизации."); return redirect(url_for("home"))
    if verify_telegram_auth(data):
        session["tg"] = {k:data.get(k) for k in ("id","first_name","last_name","username","photo_url")}
        username = data.get("username")
        row = None
        if username:
            cur = execute("SELECT * FROM users WHERE LOWER(telegram)=LOWER(?)", ("@"+username,))
            row = cur.fetchone()
        if not row:
            name = ((data.get("first_name") or "") + " " + (data.get("last_name") or "")).strip() or (username or "")
            insert_and_get_id("INSERT INTO users (name, telegram) VALUES (?,?)", (name, "@"+username if username else ""))
        flash(f"{t('hello')}, {data.get('first_name','')}!")
    else:
        flash("Telegram auth failed. Проверь токен/подпись.")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.pop("tg", None); flash("Logged out."); return redirect(url_for("home"))

# ---- Pages
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/init")
def init_route():
    init_db(); flash("Database initialized."); return redirect(url_for("home"))

@app.route("/register", methods=["GET","POST"])
def register():
    tags = execute("SELECT * FROM service_tags ORDER BY name ASC").fetchall()
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip()
        location = request.form.get("location","").strip()
        telegram = request.form.get("telegram","").strip()
        website = request.form.get("website","").strip()
        bio = request.form.get("bio","").strip()
        skills = request.form.get("skills","").strip()
        if not name:
            flash("Укажите имя."); return render_template("register.html", tags=tags, form=request.form)
        uid = insert_and_get_id(
            "INSERT INTO users (name, email, location, telegram, website, bio, skills) VALUES (?,?,?,?,?,?,?)",
            (name, email, location, telegram, website, bio, skills)
        )
        for tag_id in request.form.getlist("service_tags"):
            execute("INSERT INTO user_service_tags (user_id, tag_id) VALUES (?,?)", (uid, tag_id))
        commit()
        flash("Профиль сохранён."); return redirect(url_for("profile", user_id=uid))
    form = {}
    tg = session.get("tg")
    if tg:
        form["name"] = (tg.get("first_name","") + " " + tg.get("last_name","")).strip()
        form["telegram"] = "@"+tg["username"] if tg.get("username") else ""
    return render_template("register.html", tags=tags, form=form)

@app.route("/people")
def people():
    q = request.args.get("q","").strip().lower()
    query = (
        "SELECT u.*, "
        + ("STRING_AGG(st.name, ', ') AS services" if is_postgres() else "GROUP_CONCAT(st.name, ', ') AS services")
        + " FROM users u "
          "LEFT JOIN user_service_tags ust ON u.id=ust.user_id "
          "LEFT JOIN service_tags st ON st.id=ust.tag_id "
          "WHERE 1=1"
    )
    params = []
    if q:
        query += " AND (LOWER(u.name) LIKE ? OR LOWER(u.bio) LIKE ? OR LOWER(u.skills) LIKE ?)"
        like = f"%{q}%"; params += [like, like, like]
    query += " GROUP BY u.id ORDER BY u.created_at DESC"
    users = execute(query, params).fetchall()
    return render_template("people.html", users=users, q=q)

@app.route("/profile/<int:user_id>")
def profile(user_id):
    u = execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not u:
        flash("Пользователь не найден."); return redirect(url_for("people"))
    tags = execute(
        "SELECT st.* FROM service_tags st JOIN user_service_tags ust ON st.id=ust.tag_id WHERE ust.user_id=?",
        (user_id,)
    ).fetchall()
    return render_template("profile.html", user=u, tags=tags)

if __name__ == "__main__":
    if not is_postgres() and not os.path.exists(DATABASE_PATH):
        with app.app_context(): init_db()
    port = int(os.environ.get("PORT","5000"))
    if "--port" in sys.argv:
        i = sys.argv.index("--port")
        if i+1 < len(sys.argv): port = int(sys.argv[i+1])
    app.run(host="0.0.0.0", port=port, debug=False)
