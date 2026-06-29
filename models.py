from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)

    permissions = db.relationship("TimelinePermission", backref="user",
                                  cascade="all, delete-orphan")


class TimelinePermission(db.Model):
    __tablename__ = "timeline_permissions"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timeline_id = db.Column(db.Integer, db.ForeignKey("timelines.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "timeline_id",
                                          name="uq_user_timeline"),)


class TimelineImage(db.Model):
    __tablename__ = "timeline_images"

    id          = db.Column(db.Integer, primary_key=True)
    timeline_id = db.Column(db.Integer, db.ForeignKey("timelines.id"), nullable=True)
    filename    = db.Column(db.String(300), nullable=False)
    mimetype    = db.Column(db.String(100), nullable=False, default="image/jpeg")
    data        = db.Column(db.LargeBinary, nullable=False)


class TimelineMap(db.Model):
    __tablename__ = "timeline_maps"

    id          = db.Column(db.Integer, primary_key=True)
    timeline_id = db.Column(db.Integer, db.ForeignKey("timelines.id"), nullable=True)
    filename    = db.Column(db.String(300), nullable=False)
    mimetype    = db.Column(db.String(100), nullable=False, default="image/jpeg")
    data        = db.Column(db.LargeBinary, nullable=False)


class Timeline(db.Model):
    __tablename__ = "timelines"

    id             = db.Column(db.Integer, primary_key=True)
    title          = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    timeline_image = db.Column(db.String(300), nullable=True)
    image_id       = db.Column(db.Integer, nullable=True)

    roles  = db.relationship("Role",  backref="timeline", cascade="all, delete-orphan")
    events = db.relationship("Event", backref="timeline", cascade="all, delete-orphan")
    permissions = db.relationship("TimelinePermission", backref="timeline",
                                  cascade="all, delete-orphan")


class Role(db.Model):
    __tablename__ = "roles"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, default=0)

    timeline_id = db.Column(db.Integer, db.ForeignKey("timelines.id"), nullable=False)

    events = db.relationship("Event", backref="role", cascade="all, delete-orphan")


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)

    title       = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)

    start_text = db.Column(db.String(20), nullable=True)
    end_text   = db.Column(db.String(20), nullable=True)

    start_sort = db.Column(db.Integer, nullable=True)
    end_sort   = db.Column(db.Integer, nullable=True)

    event_image    = db.Column(db.String(300), nullable=True)
    maps_id        = db.Column(db.String(300), nullable=True)
    event_image_id = db.Column(db.Integer, db.ForeignKey("timeline_images.id"), nullable=True)
    map_asset_id   = db.Column(db.Integer, db.ForeignKey("timeline_maps.id"), nullable=True)

    timeline_id = db.Column(db.Integer, db.ForeignKey("timelines.id"), nullable=False)
    role_id     = db.Column(db.Integer, db.ForeignKey("roles.id"),     nullable=False)
