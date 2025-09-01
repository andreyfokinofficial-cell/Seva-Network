from flask import Flask, render_template, request, redirect, url_for, g, flash, session
import sqlite3, os, sys

# Database path from env (works on Render with a mounted disk)
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "seva.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY","dev-key")

SUPPORTED_LANGS = ["ru","en"]
def t(key):
    lang = session.get("lang","ru")
    return I18N.get(lang, I18N["ru"]).get(key, key)

I18N = {
    "ru": {
        "app_title": "Seva Network",
        "hero_title": "Найди единомышленников для служения и проектов",
        "hero_sub": "Создай профиль, отметь виды служения и навыки — находи людей и команды по миссии, локации и ролям.",
        "create_profile": "Создать профиль",
        "browse_people": "Посмотреть участников",
        "how_it_works": "Как это работает",
        "step_profile": "<strong>Профиль.</strong> Кто ты, где, чем можешь служить.",
        "step_search": "<strong>Поиск.</strong> Фильтры по локации и видам служения.",
        "step_contact": "<strong>Контакт.</strong> Свяжись напрямую: Telegram, сайт, email.",
        "people": "Участники",
        "projects": "Проекты",
        "new_project": "Создать проект",
        "create_project": "Создать проект",
        "project_list": "Список проектов",
        "name": "Имя",
        "email": "Email",
        "location": "Локация",
        "telegram": "Telegram",
        "website": "Сайт/Портфолио",
        "about": "О себе",
        "services": "Виды служения (теги)",
        "skills": "Навыки и опыт",
        "availability": "Доступность",
        "save": "Сохранить",
        "cancel": "Отмена",
        "filters": "Фильтры",
        "query": "Имя / навыки / о себе",
        "service": "Вид служения",
        "find": "Найти",
        "not_found": "Пока никого не найдено. Попробуйте изменить параметры поиска.",
        "contacts": "Контакты",
        "profile_created": "Профиль создан!",
        "user_not_found": "Пользователь не найден.",
        "reinit": "(Re)Init DB",
        "project_title": "Название проекта",
        "mission": "Миссия/описание",
        "needs": "Какие роли нужны (перечислите)",
        "links": "Полезные ссылки",
        "owner_email": "Email владельца проекта",
        "project_created": "Проект создан!",
        "project_not_found": "Проект не найден.",
        "needed_roles": "Нужные роли",
        "back_to_people": "Назад к участникам",
        "back_to_projects": "Назад к проектам",
        "lang": "Язык",
    },
    "en": {
        "app_title": "Seva Network",
        "hero_title": "Find collaborators for seva and purpose-driven projects",
        "hero_sub": "Create a profile, mark service types and skills — find people and teams by mission, location, and roles.",
        "create_profile": "Create Profile",
        "browse_people": "Browse People",
        "how_it_works": "How it works",
        "step_profile": "<strong>Profile.</strong> Who you are, where you are, how you can serve.",
        "step_search": "<strong>Search.</strong> Filter by location and service types.",
        "step_contact": "<strong>Contact.</strong> Reach out via Telegram, website, email.",
        "people": "People",
        "projects": "Projects",
        "new_project": "Create project",
        "create_project": "Create project",
        "project_list": "Project list",
        "name": "Name",
        "email": "Email",
        "location": "Location",
        "telegram": "Telegram",
        "website": "Website/Portfolio",
        "about": "About",
        "services": "Service tags",
        "skills": "Skills & experience",
        "availability": "Availability",
        "save": "Save",
        "cancel": "Cancel",
        "filters": "Filters",
        "query": "Name / skills / about",
        "service": "Service type",
        "find": "Find",
        "not_found": "No one found yet. Try adjusting your search.",
        "contacts": "Contacts",
        "profile_created": "Profile created!",
        "user_not_found": "User not found.",
        "reinit": "(Re)Init DB",
        "project_title": "Project title",
        "mission": "Mission/description",
        "needs": "Needed roles (comma-separated)",
        "links": "Useful links",
        "owner_email": "Project owner email",
        "project_created": "Project created!",
        "project_not_found": "Project not found.",
        "needed_roles": "Needed roles",
        "back_to_people": "Back to people",
        "back_to_projects": "Back to projects",
        "lang": "Language",
    }
}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r', encoding='utf-8') as f:
            db.executescript(f.read())
        # Seed service tags
        seed_tags = [
            ("киртан/киртана","music"),
            ("кулинария/прасад","food"),
            ("дизайн","creative"),
            ("перевод","language"),
            ("фандрайзинг","fundraising"),
            ("санкиртана","outreach"),
            ("медиа/видео","media"),
            ("соцсети/PR","media"),
            ("образование/лекции","education"),
            ("организация/ивенты","events"),
        ]
        db.executemany("INSERT INTO service_tags (name, category) VALUES (?,?)", seed_tags)
        db.commit()

@app.route('/init')
def init_route():
    init_db()
    flash("Database initialized.")
    return redirect(url_for('home'))

@app.route('/lang/<code>')
def set_lang(code):
    if code in SUPPORTED_LANGS:
        session['lang'] = code
    return redirect(request.referrer or url_for('home'))

@app.route('/')
def home():
    return render_template('home.html', t=t)

@app.route('/register', methods=['GET','POST'])
def register():
    db = get_db()
    tags = db.execute("SELECT * FROM service_tags ORDER BY name ASC").fetchall()
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        location = request.form.get('location','').strip()
        telegram = request.form.get('telegram','').strip()
        website = request.form.get('website','').strip()
        bio = request.form.get('bio','').strip()
        skills = request.form.get('skills','').strip()
        availability = request.form.get('availability','').strip()
        selected = request.form.getlist('service_tags')
        if not name or not email:
            flash("Name and Email are required.")
            return render_template('register.html', t=t, tags=tags, form=request.form)
        cur = db.execute(
            '''INSERT INTO users (name, email, location, telegram, website, bio, skills, availability)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, email, location, telegram, website, bio, skills, availability)
        )
        user_id = cur.lastrowid
        for tag_id in selected:
            db.execute("INSERT INTO user_service_tags (user_id, tag_id) VALUES (?,?)", (user_id, tag_id))
        db.commit()
        flash(t("profile_created"))
        return redirect(url_for('profile', user_id=user_id))
    return render_template('register.html', t=t, tags=tags, form=None)

@app.route('/people')
def people():
    db = get_db()
    q = request.args.get('q','').strip()
    location = request.args.get('location','').strip()
    tag_ids = request.args.getlist('tag')
    # Base query
    query = "SELECT u.*, GROUP_CONCAT(st.name, ', ') AS services FROM users u LEFT JOIN user_service_tags ust ON u.id=ust.user_id LEFT JOIN service_tags st ON ust.tag_id=st.id WHERE 1=1"
    params = []
    if q:
        query += " AND (LOWER(u.name) LIKE ? OR LOWER(u.bio) LIKE ? OR LOWER(u.skills) LIKE ?)"
        like = f"%{q.lower()}%"
        params.extend([like, like, like])
    if location:
        query += " AND LOWER(u.location) LIKE ?"
        params.append(f"%{location.lower()}%")
    if tag_ids:
        # Ensure the user has ALL selected tags
        placeholders = ",".join(["?"]*len(tag_ids))
        query += f" AND u.id IN (SELECT user_id FROM user_service_tags WHERE tag_id IN ({placeholders}) GROUP BY user_id HAVING COUNT(DISTINCT tag_id)=?)"
        params.extend(tag_ids)
        params.append(len(tag_ids))
    query += " GROUP BY u.id ORDER BY u.created_at DESC"
    users = db.execute(query, params).fetchall()
    tags = db.execute("SELECT * FROM service_tags ORDER BY name ASC").fetchall()
    return render_template('people.html', t=t, users=users, tags=tags, q=q, location=location, tag_ids=[int(x) for x in tag_ids])

@app.route('/profile/<int:user_id>')
def profile(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        flash(t("user_not_found"))
        return redirect(url_for('people'))
    tags = db.execute("SELECT st.* FROM service_tags st JOIN user_service_tags ust ON st.id=ust.tag_id WHERE ust.user_id=?", (user_id,)).fetchall()
    return render_template('profile.html', t=t, user=user, tags=tags)

@app.route('/projects')
def project_list():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return render_template('projects.html', t=t, projects=projects)

@app.route('/projects/new', methods=['GET','POST'])
def project_new():
    db = get_db()
    tags = db.execute("SELECT * FROM service_tags ORDER BY name ASC").fetchall()
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        mission = request.form.get('mission','').strip()
        needs = request.form.get('needs','').strip()
        links = request.form.get('links','').strip()
        owner = request.form.get('owner_email','').strip()
        selected = request.form.getlist('service_tags')
        if not title or not owner:
            flash("Title and Owner email are required.")
            return render_template('project_new.html', t=t, tags=tags, form=request.form)
        cur = db.execute("INSERT INTO projects (title, mission, needs, links, owner_email) VALUES (?,?,?,?,?)", (title, mission, needs, links, owner))
        pid = cur.lastrowid
        for tag_id in selected:
            db.execute("INSERT INTO project_tags (project_id, tag_id) VALUES (?,?)", (pid, tag_id))
        db.commit()
        flash(t("project_created"))
        return redirect(url_for('project_view', project_id=pid))
    return render_template('project_new.html', t=t, tags=tags, form=None)

@app.route('/projects/<int:project_id>')
def project_view(project_id):
    db = get_db()
    pr = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not pr:
        flash(t("project_not_found"))
        return redirect(url_for('project_list'))
    tags = db.execute("SELECT st.* FROM service_tags st JOIN project_tags pt ON st.id=pt.tag_id WHERE pt.project_id=?", (project_id,)).fetchall()
    members = db.execute("SELECT u.* FROM users u JOIN project_members pm ON u.id=pm.user_id WHERE pm.project_id=?", (project_id)).fetchall()
    return render_template('project_view.html', t=t, project=pr, tags=tags, members=members)

if __name__ == "__main__":
    # Local dev: init DB if missing
    init_if_missing = not os.path.exists(DATABASE)
    if init_if_missing:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True) if os.path.dirname(DATABASE) else None
        with app.app_context():
            init_db()

    # Port override via CLI: python app.py --port 5001
    port = int(os.environ.get("PORT", "5000"))
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    # In production, run via gunicorn (wsgi:application). This branch is for dev only.
    app.run(host="0.0.0.0", port=port, debug=False)
