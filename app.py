import os
import shutil
import signal
import subprocess
import threading
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, abort, make_response, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.pool import NullPool
from models import db, Timeline, Role, Event, User, TimelinePermission, TimelineImage, TimelineMap

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlite3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# NullPool opens a fresh SQLite connection per request — required when
# gunicorn runs multiple worker processes, otherwise each worker caches
# its own connection and reads stale data after another worker commits.
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'poolclass': NullPool}
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

db.init_app(app)

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif"}

_MIME_MAP = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
}

def _ext_mimetype(ext):
    return _MIME_MAP.get(ext.lower(), "application/octet-stream")


# ── Disk-path helpers (used only by migrate_db.py) ────────────────────────────

def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def timeline_images_dir(timeline_id):
    return _ensure_dir(os.path.join("static", "timeline_images", str(timeline_id)))

def timeline_maps_dir(timeline_id):
    return _ensure_dir(os.path.join("static", "timeline_maps", str(timeline_id)))


# ── Database-backed asset helpers ─────────────────────────────────────────────

def get_timeline_images(timeline_id):
    return (TimelineImage.query
            .filter_by(timeline_id=timeline_id)
            .order_by(TimelineImage.filename)
            .all())


def get_timeline_maps(timeline_id):
    return (TimelineMap.query
            .filter_by(timeline_id=timeline_id)
            .order_by(TimelineMap.filename)
            .all())


def get_images():
    return (TimelineImage.query
            .filter_by(timeline_id=None)
            .order_by(TimelineImage.filename)
            .all())


# ── Date helpers ──────────────────────────────────────────────────────────────

def normalise_date(text):
    if not text:
        return None
    parts = text.split("-")
    if len(parts) == 3:
        dd, mm, yyyy = parts
    elif len(parts) == 2:
        dd = "00"
        mm, yyyy = parts
    else:
        dd = "00"
        mm = "00"
        yyyy = parts[0]
    return int(f"{yyyy}{mm}{dd}")


def to_iso(text):
    if not text:
        return None
    parts = text.split("-")
    if len(parts) == 3:
        d, m, y = parts
        return f"{y}-{m}-{d}"
    if len(parts) == 2:
        m, y = parts
        return f"{y}-{m}-01"
    if len(parts) == 1:
        y = parts[0]
        return f"{y}-01-01"
    return None


def display_date(text):
    return text if text else ""


app.jinja_env.globals['display_date'] = display_date


# ── Blob-serve routes ─────────────────────────────────────────────────────────

_SAFE_IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

@app.route("/image/<int:image_id>")
def serve_image(image_id):
    img = TimelineImage.query.get_or_404(image_id)
    ct  = img.mimetype if img.mimetype in _SAFE_IMAGE_MIMES else "application/octet-stream"
    resp = make_response(img.data)
    resp.headers["Content-Type"]           = ct
    resp.headers["Cache-Control"]          = "public, max-age=31536000, immutable"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/map/<int:map_id>")
def serve_map(map_id):
    m  = TimelineMap.query.get_or_404(map_id)
    ct = m.mimetype if m.mimetype in _SAFE_IMAGE_MIMES else "application/octet-stream"
    resp = make_response(m.data)
    resp.headers["Content-Type"]           = ct
    resp.headers["Cache-Control"]          = "public, max-age=31536000, immutable"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


# ── Auth helpers ───────────────────────────────────────────────────────────────

def get_current_user():
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for('login'))
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def can_edit_timeline(timeline_id):
    user = get_current_user()
    if not user:
        return False
    if user.is_admin:
        return True
    return TimelinePermission.query.filter_by(
        user_id=user.id, timeline_id=timeline_id
    ).first() is not None


@app.context_processor
def inject_current_user():
    return dict(current_user=get_current_user())


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if User.query.count() > 0:
        flash("Setup already complete. Please log in.", "error")
        return redirect(url_for('login'))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("setup.html")
        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            is_admin=True
        )
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        flash(f"Admin account '{username}' created. Welcome!", "success")
        return redirect(url_for('home'))
    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    if User.query.count() == 0:
        return redirect(url_for('setup'))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for('home'))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))


# ── Admin – user management ────────────────────────────────────────────────────

@app.route("/admin/users")
@admin_required
def admin_users():
    users     = User.query.order_by(User.username).all()
    timelines = Timeline.query.order_by(Timeline.title).all()
    perms = {(p.user_id, p.timeline_id)
             for p in TimelinePermission.query.all()}
    return render_template("admin_users.html",
                           users=users, timelines=timelines, perms=perms)


@app.route("/admin/users/add", methods=["POST"])
@admin_required
def admin_add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    is_admin = bool(request.form.get("is_admin"))
    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for('admin_users'))
    if User.query.filter_by(username=username).first():
        flash(f"Username '{username}' already exists.", "error")
        return redirect(url_for('admin_users'))
    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        is_admin=is_admin
    )
    db.session.add(user)
    db.session.commit()
    flash(f"User '{username}' created.", "success")
    return redirect(url_for('admin_users'))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session.get('user_id'):
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('admin_users'))
    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash("Cannot delete the only administrator account.", "error")
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' deleted.", "success")
    return redirect(url_for('admin_users'))


@app.route("/admin/update", methods=["POST"])
@admin_required
def admin_update():
    app_dir = os.path.dirname(os.path.abspath(__file__))

    venv_pip    = os.path.join(app_dir, "venv", "bin", "pip")
    venv_python = os.path.join(app_dir, "venv", "bin", "python")
    pip_cmd    = venv_pip    if os.path.exists(venv_pip)    else "pip3"
    python_cmd = venv_python if os.path.exists(venv_python) else "python3"

    db_path  = os.path.join(app_dir, "instance", "sqlite3.db")
    db_backup = db_path + ".bak"

    # Protect the live database: git pull overwrites tracked files,
    # which would restore the Replit dev db on top of the Pi's data.
    if os.path.exists(db_path):
        shutil.copy2(db_path, db_backup)

    ssh_env = {**os.environ,
               "GIT_SSH_COMMAND": "ssh -o StrictHostKeyChecking=no -o BatchMode=yes"}

    steps = [
        ("Pulling latest code",
         ["git", "-C", app_dir, "pull", "--ff-only", "origin", "master"],
         ssh_env),
        ("Updating dependencies",
         [pip_cmd, "install", "-r", os.path.join(app_dir, "requirements.txt"), "-q"],
         None),
        ("Applying DB migrations",
         [python_cmd, os.path.join(app_dir, "migrate_db.py")],
         None),
    ]

    all_ok = True
    for label, cmd, env in steps:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                env=env if env is not None else os.environ.copy()
            )
            if result.returncode != 0:
                flash(f"{label} failed: {(result.stderr or result.stdout).strip()}", "error")
                all_ok = False
            else:
                flash(f"✓ {label}", "success")
        except subprocess.TimeoutExpired:
            flash(f"{label} timed out.", "error")
            all_ok = False
        except Exception as exc:
            flash(f"{label} error: {exc}", "error")
            all_ok = False

    # Always restore the live database after the pull — git pull overwrites
    # tracked files, which would replace the Pi db with the Replit dev copy.
    if os.path.exists(db_backup):
        shutil.copy2(db_backup, db_path)
        os.remove(db_backup)

    if all_ok:
        flash("Update complete — app is reloading.", "success")
        # Delay the SIGHUP so this response is delivered before workers restart
        def _reload():
            import time
            time.sleep(1)
            try:
                os.kill(os.getppid(), signal.SIGHUP)
            except Exception:
                pass
        threading.Thread(target=_reload, daemon=True).start()

    return redirect(url_for("home"))


@app.route("/admin/db/backup")
@admin_required
def admin_db_backup():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "sqlite3.db")
    if not os.path.exists(db_path):
        flash("Database file not found.", "error")
        return redirect(url_for("home"))
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        db_path,
        as_attachment=True,
        download_name=f"timeline_backup_{timestamp}.db",
        mimetype="application/octet-stream",
    )


@app.route("/admin/db/restore", methods=["POST"])
@admin_required
def admin_db_restore():
    f = request.files.get("db_file")
    if not f or not f.filename:
        flash("No file selected.", "error")
        return redirect(url_for("home"))
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "sqlite3.db")
    db_backup = db_path + ".pre_restore.bak"
    try:
        if os.path.exists(db_path):
            shutil.copy2(db_path, db_backup)
        f.save(db_path)
        flash("Database restored successfully. The app will reload.", "success")
        def _reload():
            import time
            time.sleep(1)
            try:
                os.kill(os.getppid(), signal.SIGHUP)
            except Exception:
                pass
        threading.Thread(target=_reload, daemon=True).start()
    except Exception as exc:
        if os.path.exists(db_backup):
            shutil.copy2(db_backup, db_path)
        flash(f"Restore failed: {exc}", "error")
    finally:
        if os.path.exists(db_backup):
            os.remove(db_backup)
    return redirect(url_for("home"))


@app.route("/admin/users/<int:user_id>/permissions", methods=["POST"])
@admin_required
def admin_update_permissions(user_id):
    user = User.query.get_or_404(user_id)
    is_admin = bool(request.form.get("is_admin"))
    if not is_admin and user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash("Cannot remove admin status — at least one administrator must exist.", "error")
        return redirect(url_for('admin_users'))
    if user.id == session.get('user_id') and not is_admin:
        flash("You cannot remove your own admin status.", "error")
        return redirect(url_for('admin_users'))
    user.is_admin = is_admin
    # Optional password reset
    new_password = request.form.get("new_password", "").strip()
    if new_password:
        user.password_hash = generate_password_hash(new_password)
    # Rebuild timeline permissions
    selected = {int(x) for x in request.form.getlist("timeline_ids")}
    TimelinePermission.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    for tid in selected:
        db.session.add(TimelinePermission(user_id=user_id, timeline_id=tid))
    db.session.commit()
    flash(f"Permissions updated for '{user.username}'.", "success")
    return redirect(url_for('admin_users'))


# ── Home ──────────────────────────────────────────────────────────────────────

ROLE_COLOURS = [
    '#c8703a', '#4a90c8', '#5aaa5a', '#c85aaa', '#aaaa3a',
    '#3aaaaa', '#c89050', '#705ac8', '#c84a4a', '#3ac870'
]


@app.route("/")
def home():
    timelines = Timeline.query.order_by(Timeline.title).all()
    timeline_info = []
    for tl in timelines:
        events      = tl.events
        event_count = len(events)
        date_range  = None
        if event_count > 0:
            start_sorts = [e.start_sort for e in events if e.start_sort]
            end_sorts   = [e.end_sort   for e in events if e.end_sort]
            all_sorts   = start_sorts + end_sorts
            if start_sorts:
                min_year = min(start_sorts) // 10000
                max_year = max(all_sorts)   // 10000
                date_range = (str(min_year) if min_year == max_year
                              else f"{min_year} – {max_year}")
        timeline_info.append({
            'timeline':    tl,
            'event_count': event_count,
            'date_range':  date_range,
        })
    user = get_current_user()
    if user:
        if user.is_admin:
            editable_ids = {info['timeline'].id for info in timeline_info}
        else:
            editable_ids = {p.timeline_id for p in user.permissions}
    else:
        editable_ids = set()

    return render_template("home.html", timeline_info=timeline_info,
                           editable_ids=editable_ids)


# ── View timeline ─────────────────────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>")
def view_timeline(timeline_id):
    timeline = Timeline.query.get_or_404(timeline_id)

    items = []
    for ev in timeline.events:
        if ev.event_image_id:
            content_html = (
                f"<img src='/image/{ev.event_image_id}' "
                f"style='height:40px; vertical-align:middle; margin-right:6px;'> "
                f"{ev.title}"
            )
        else:
            content_html = ev.title

        items.append({
            "id":          ev.id,
            "content":     content_html,
            "start":       to_iso(ev.start_text),
            "end":         to_iso(ev.end_text),
            "group":       ev.role_id,
            "description": ev.description or "",
            "maps_id":     ev.map_asset_id or ""
        })

    sorted_roles = (Role.query
                    .filter_by(timeline_id=timeline_id)
                    .order_by(Role.sort_order)
                    .all())
    groups = [{
        "id":      role.id,
        "content": role.name,
        "order":   role.sort_order,
        "colour":  ROLE_COLOURS[i % len(ROLE_COLOURS)],
    } for i, role in enumerate(sorted_roles)]

    if timeline.image_id:
        tl_img_url = f"/image/{timeline.image_id}"
    else:
        tl_img_url = "/static/images/bg_castle.jpg"

    return render_template(
        "view_timeline.html",
        timeline=timeline,
        timeline_image_url=tl_img_url,
        items=items,
        groups=groups,
        can_edit=can_edit_timeline(timeline_id)
    )


# ── Add event ─────────────────────────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>/event/add", methods=["GET", "POST"])
@login_required
def add_event(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    tl    = Timeline.query.get_or_404(timeline_id)
    roles = Role.query.filter_by(timeline_id=timeline_id).order_by(Role.sort_order).all()

    if request.method == "POST":
        _img_val = request.form.get("event_image_id")
        _map_val = request.form.get("map_asset_id")
        _img_id  = int(_img_val) if _img_val else None
        _map_id  = int(_map_val) if _map_val else None
        if _img_id and not TimelineImage.query.filter_by(id=_img_id, timeline_id=timeline_id).first():
            _img_id = None
        if _map_id and not TimelineMap.query.filter_by(id=_map_id, timeline_id=timeline_id).first():
            _map_id = None
        ev = Event(
            title          = request.form["title"],
            start_text     = request.form["start_text"],
            end_text       = request.form["end_text"],
            description    = request.form["description"],
            role_id        = request.form.get("role_id"),
            timeline_id    = timeline_id,
            event_image_id = _img_id,
            map_asset_id   = _map_id,
        )
        ev.start_sort = normalise_date(ev.start_text)
        ev.end_sort   = normalise_date(ev.end_text)
        db.session.add(ev)
        db.session.commit()
        flash("Event added", "success")
        return redirect(url_for("view_timeline", timeline_id=timeline_id))

    return render_template(
        "add_event.html",
        timeline=tl,
        roles=roles,
        images=get_timeline_images(timeline_id),
        maps=get_timeline_maps(timeline_id)
    )


# ── Edit event ────────────────────────────────────────────────────────────────

@app.route("/event/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    ev = Event.query.get_or_404(event_id)
    if not can_edit_timeline(ev.timeline_id):
        abort(403)
    tl    = ev.timeline
    roles = Role.query.filter_by(timeline_id=tl.id).order_by(Role.sort_order).all()

    if request.method == "POST":
        ev.title       = request.form["title"]
        ev.start_text  = request.form["start_text"]
        ev.end_text    = request.form["end_text"]
        ev.start_sort  = normalise_date(ev.start_text)
        ev.end_sort    = normalise_date(ev.end_text)
        ev.description = request.form["description"]
        ev.role_id = request.form.get("role_id")
        _img_val  = request.form.get("event_image_id")
        _map_val  = request.form.get("map_asset_id")
        _img_id   = int(_img_val) if _img_val else None
        _map_id   = int(_map_val) if _map_val else None
        if _img_id and not TimelineImage.query.filter_by(id=_img_id, timeline_id=ev.timeline_id).first():
            _img_id = None
        if _map_id and not TimelineMap.query.filter_by(id=_map_id, timeline_id=ev.timeline_id).first():
            _map_id = None
        ev.event_image_id = _img_id
        ev.map_asset_id   = _map_id
        db.session.commit()
        flash("Event updated", "success")
        return redirect(url_for("view_timeline", timeline_id=tl.id))

    return render_template(
        "edit_event.html",
        event=ev,
        timeline=tl,
        roles=roles,
        images=get_timeline_images(tl.id),
        maps=get_timeline_maps(tl.id)
    )


# ── Delete event ──────────────────────────────────────────────────────────────

@app.route("/event/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    if not can_edit_timeline(event.timeline_id):
        abort(403)
    timeline_id = event.timeline_id
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "success")
    return redirect(url_for("view_timeline", timeline_id=timeline_id))


# ── Manage assets ─────────────────────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>/assets")
@login_required
def manage_assets(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    tl     = Timeline.query.get_or_404(timeline_id)
    images = get_timeline_images(timeline_id)
    maps   = get_timeline_maps(timeline_id)
    return render_template("manage_assets.html", timeline=tl, images=images, maps=maps)


@app.route("/timeline/<int:timeline_id>/assets/upload_image", methods=["POST"])
@login_required
def upload_image(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    Timeline.query.get_or_404(timeline_id)
    f = request.files.get("image_file")
    if not f or not f.filename:
        flash("No file selected.", "error")
        return redirect(url_for("manage_assets", timeline_id=timeline_id))
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        flash("Invalid file type. Allowed: jpg, jpeg, png, gif.", "error")
        return redirect(url_for("manage_assets", timeline_id=timeline_id))
    name = secure_filename(f.filename)
    img = TimelineImage(
        timeline_id=timeline_id,
        filename=name,
        mimetype=_ext_mimetype(ext),
        data=f.read(),
    )
    db.session.add(img)
    db.session.commit()
    flash(f"Image '{name}' uploaded.", "success")
    return redirect(url_for("manage_assets", timeline_id=timeline_id))


@app.route("/timeline/<int:timeline_id>/assets/upload_map", methods=["POST"])
@login_required
def upload_map(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    Timeline.query.get_or_404(timeline_id)
    f = request.files.get("map_file")
    if not f or not f.filename:
        flash("No file selected.", "error")
        return redirect(url_for("manage_assets", timeline_id=timeline_id))
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png"}:
        flash("Invalid file type. Allowed: jpg, jpeg, png.", "error")
        return redirect(url_for("manage_assets", timeline_id=timeline_id))
    name = secure_filename(f.filename)
    m = TimelineMap(
        timeline_id=timeline_id,
        filename=name,
        mimetype=_ext_mimetype(ext),
        data=f.read(),
    )
    db.session.add(m)
    db.session.commit()
    flash(f"Map '{name}' uploaded.", "success")
    return redirect(url_for("manage_assets", timeline_id=timeline_id))


@app.route("/timeline/<int:timeline_id>/assets/delete_image/<int:image_id>",
           methods=["POST"])
@login_required
def delete_image(timeline_id, image_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    Timeline.query.get_or_404(timeline_id)
    img = TimelineImage.query.get_or_404(image_id)
    if img.timeline_id != timeline_id:
        abort(403)
    Event.query.filter_by(event_image_id=image_id).update({"event_image_id": None})
    Timeline.query.filter_by(image_id=image_id).update({"image_id": None})
    db.session.delete(img)
    db.session.commit()
    flash(f"Image '{img.filename}' deleted.", "success")
    return redirect(url_for("manage_assets", timeline_id=timeline_id))


@app.route("/timeline/<int:timeline_id>/assets/delete_map/<int:map_id>",
           methods=["POST"])
@login_required
def delete_map(timeline_id, map_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    Timeline.query.get_or_404(timeline_id)
    m = TimelineMap.query.get_or_404(map_id)
    if m.timeline_id != timeline_id:
        abort(403)
    Event.query.filter_by(map_asset_id=map_id).update({"map_asset_id": None})
    db.session.delete(m)
    db.session.commit()
    flash(f"Map '{m.filename}' deleted.", "success")
    return redirect(url_for("manage_assets", timeline_id=timeline_id))


# ── Manage roles ──────────────────────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>/roles")
@login_required
def manage_roles(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    tl    = Timeline.query.get_or_404(timeline_id)
    roles = Role.query.filter_by(timeline_id=timeline_id).order_by(Role.sort_order).all()
    return render_template("manage_roles.html", timeline=tl, roles=roles)


@app.route("/timeline/<int:timeline_id>/roles/add", methods=["POST"])
@login_required
def add_role(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    Timeline.query.get_or_404(timeline_id)
    existing_roles = Role.query.filter_by(timeline_id=timeline_id).count()
    if existing_roles >= 50:
        flash("Maximum of 50 roles allowed per timeline.", "error")
        return redirect(url_for("manage_roles", timeline_id=timeline_id))
    role = Role(
        name=request.form["name"],
        sort_order=existing_roles + 1,
        timeline_id=timeline_id
    )
    db.session.add(role)
    db.session.commit()
    flash("Role added.", "success")
    return redirect(url_for("manage_roles", timeline_id=timeline_id))


# ── Add timeline (admin only) ─────────────────────────────────────────────────

@app.route("/timeline/add", methods=["GET", "POST"])
@admin_required
def add_timeline():
    if request.method == "POST":
        _img_val = request.form.get("timeline_image")
        _img_id  = int(_img_val) if _img_val else None
        if _img_id and not TimelineImage.query.filter_by(id=_img_id, timeline_id=None).first():
            _img_id = None
        tl = Timeline(
            title       = request.form["title"],
            description = request.form["description"],
            image_id    = _img_id,
        )
        db.session.add(tl)
        db.session.commit()
        flash("Timeline created", "success")
        return redirect(url_for("home"))
    return render_template("add_timeline.html", images=get_images())


# ── Edit timeline ─────────────────────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>/edit", methods=["GET", "POST"])
@login_required
def edit_timeline(timeline_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    tl     = Timeline.query.get_or_404(timeline_id)
    images = get_images()
    if request.method == "POST":
        tl.title       = request.form["title"]
        tl.description = request.form["description"]
        _img_val = request.form.get("timeline_image")
        _img_id  = int(_img_val) if _img_val else None
        if _img_id and not TimelineImage.query.filter_by(id=_img_id, timeline_id=None).first():
            _img_id = None
        tl.image_id = _img_id
        db.session.commit()
        flash("Timeline updated.", "success")
        return redirect(url_for("home"))
    return render_template("edit_timeline.html", timeline=tl, images=images)


# ── Delete timeline (admin only) ──────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>/delete", methods=["POST"])
@admin_required
def delete_timeline(timeline_id):
    tl = Timeline.query.get_or_404(timeline_id)
    db.session.delete(tl)
    db.session.commit()
    flash("Timeline deleted.", "success")
    return redirect(url_for("home"))


# ── Role reordering & deletion ────────────────────────────────────────────────

@app.route("/timeline/<int:timeline_id>/roles/<int:role_id>/move/<direction>",
           methods=["POST"])
@login_required
def move_role(timeline_id, role_id, direction):
    if not can_edit_timeline(timeline_id):
        abort(403)
    roles = (Role.query
             .filter_by(timeline_id=timeline_id)
             .order_by(Role.sort_order)
             .all())
    idx = next((i for i, r in enumerate(roles) if r.id == role_id), None)
    if idx is None:
        flash("Role not found.", "error")
        return redirect(url_for("manage_roles", timeline_id=timeline_id))
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(roles):
        roles[idx].sort_order, roles[swap_idx].sort_order = (
            roles[swap_idx].sort_order, roles[idx].sort_order)
        db.session.commit()
    return redirect(url_for("manage_roles", timeline_id=timeline_id))


@app.route("/timeline/<int:timeline_id>/roles/<int:role_id>/delete", methods=["POST"])
@login_required
def delete_role(timeline_id, role_id):
    if not can_edit_timeline(timeline_id):
        abort(403)
    role = Role.query.get_or_404(role_id)
    if role.timeline_id != timeline_id:
        abort(403)
    db.session.delete(role)
    db.session.commit()
    flash(f'Role "{role.name}" deleted.', "success")
    return redirect(url_for("manage_roles", timeline_id=timeline_id))


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Incremental column migrations — safe to run repeatedly
        _new_columns = [
            ("events",    "maps_id",        "VARCHAR(300) DEFAULT NULL"),
            ("events",    "event_image_id", "INTEGER DEFAULT NULL"),
            ("events",    "map_asset_id",   "INTEGER DEFAULT NULL"),
            ("timelines", "image_id",       "INTEGER DEFAULT NULL"),
        ]
        with db.engine.connect() as conn:
            for tbl, col, ddl in _new_columns:
                try:
                    conn.execute(db.text(f"ALTER TABLE {tbl} ADD COLUMN {col} {ddl}"))
                    conn.commit()
                except Exception:
                    pass

    app.run(host="0.0.0.0", port=5000, debug=True)
