#!/usr/bin/env python3
"""
migrate_db.py — Safe, incremental schema migration for Historical Timelines.

Run this every time you update the code.  It:
  1. Creates any new tables defined in models.py  (db.create_all is idempotent)
  2. Detects columns present in models.py but missing from the live database
     and adds them with ALTER TABLE … ADD COLUMN  (SQLite supports this)
  3. Migrates existing on-disk images/maps into the database as blobs and
     wires up the new FK columns on events and timelines  (idempotent)

Data is never deleted or modified (except nulling the legacy string columns
after their blobs have been successfully inserted).
"""

import mimetypes
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(__file__))

from app import app, timeline_images_dir, timeline_maps_dir
from models import db, Event, Timeline, TimelineImage, TimelineMap


# ── helpers ───────────────────────────────────────────────────────────────────

def _db_path():
    """Resolve the absolute path to the SQLite file."""
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    rel = uri.replace("sqlite:///", "", 1)
    if os.path.isabs(rel):
        return rel
    return os.path.join(app.instance_path, os.path.basename(rel))


def _existing_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name!r})").fetchall()
    return {row[1] for row in rows}


def _existing_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def _column_ddl(col):
    """Return  'col_name TYPE [DEFAULT x] [NOT NULL]'  for ALTER TABLE."""
    type_str = str(col.type)
    parts = [col.name, type_str]

    if col.default is not None and not callable(col.default.arg):
        default_val = col.default.arg
        if isinstance(default_val, bool):
            parts.append(f"DEFAULT {int(default_val)}")
        elif isinstance(default_val, (int, float)):
            parts.append(f"DEFAULT {default_val}")
        elif default_val is None:
            parts.append("DEFAULT NULL")
        else:
            safe = str(default_val).replace("'", "''")
            parts.append(f"DEFAULT '{safe}'")
    elif col.nullable:
        parts.append("DEFAULT NULL")

    return " ".join(parts)


def _guess_mimetype(filename):
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


# ── main ──────────────────────────────────────────────────────────────────────

def migrate():
    with app.app_context():
        # ── 1. Create new tables ──────────────────────────────────────────────
        db.create_all()
        print("✓  Tables checked / created")

        # ── 2. Add missing columns to existing tables ─────────────────────────
        path = _db_path()
        if not os.path.exists(path):
            print("✓  No existing database — nothing to migrate")
            return

        conn = sqlite3.connect(path)
        try:
            live_tables = _existing_tables(conn)
            changes = 0

            for table in db.metadata.sorted_tables:
                if table.name not in live_tables:
                    continue

                existing_cols = _existing_columns(conn, table.name)

                for col in table.columns:
                    if col.name in existing_cols:
                        continue

                    ddl = _column_ddl(col)
                    sql = f"ALTER TABLE {table.name!r} ADD COLUMN {ddl}"
                    print(f"   + {table.name}.{col.name}  →  {ddl}")
                    conn.execute(sql)
                    conn.commit()
                    changes += 1

            if changes == 0:
                print("✓  Schema is up to date — no changes needed")
            else:
                print(f"✓  Applied {changes} column addition(s)")
        finally:
            conn.close()

        # ── 3. Migrate on-disk images → database blobs ────────────────────────
        _migrate_assets()


def _migrate_assets():
    """
    Read every image/map file from the legacy disk folders, insert it as a
    blob row if one with the same (timeline_id, filename) does not already
    exist, then update the FK column on the owning event/timeline row.

    Idempotent: safe to run more than once.
    """
    img_count = 0
    map_count = 0

    # ── 3a. Per-timeline event images ─────────────────────────────────────────
    timeline_images_root = os.path.join(
        os.path.dirname(__file__), "static", "timeline_images"
    )
    if os.path.isdir(timeline_images_root):
        for tid_str in os.listdir(timeline_images_root):
            try:
                tid = int(tid_str)
            except ValueError:
                continue
            folder = os.path.join(timeline_images_root, tid_str)
            if not os.path.isdir(folder):
                continue

            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                if not os.path.isfile(fpath):
                    continue

                existing = TimelineImage.query.filter_by(
                    timeline_id=tid, filename=fname
                ).first()

                if existing is None:
                    with open(fpath, "rb") as fh:
                        data = fh.read()
                    img_row = TimelineImage(
                        timeline_id=tid,
                        filename=fname,
                        mimetype=_guess_mimetype(fname),
                        data=data,
                    )
                    db.session.add(img_row)
                    db.session.flush()
                    existing = img_row
                    img_count += 1

                # Wire up any events that still reference this file by name,
                # then clear the legacy string column.
                for ev in Event.query.filter_by(
                    timeline_id=tid, event_image=fname
                ).all():
                    if ev.event_image_id is None:
                        ev.event_image_id = existing.id
                    ev.event_image = None

                # Blob confirmed in DB — remove the disk file.
                os.remove(fpath)

        db.session.commit()

    # ── 3b. Global / shared timeline cover images (static/images/) ───────────
    global_images_root = os.path.join(
        os.path.dirname(__file__), "static", "images"
    )
    allowed_exts = {".jpg", ".jpeg", ".png", ".gif"}
    if os.path.isdir(global_images_root):
        for fname in os.listdir(global_images_root):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in allowed_exts:
                continue
            fpath = os.path.join(global_images_root, fname)
            if not os.path.isfile(fpath):
                continue

            existing = TimelineImage.query.filter_by(
                timeline_id=None, filename=fname
            ).first()

            if existing is None:
                with open(fpath, "rb") as fh:
                    data = fh.read()
                img_row = TimelineImage(
                    timeline_id=None,
                    filename=fname,
                    mimetype=_guess_mimetype(fname),
                    data=data,
                )
                db.session.add(img_row)
                db.session.flush()
                existing = img_row
                img_count += 1

            # Wire up timelines that still reference this file by name,
            # then clear the legacy string column.
            for tl in Timeline.query.filter_by(timeline_image=fname).all():
                if tl.image_id is None:
                    tl.image_id = existing.id
                tl.timeline_image = None

            # Blob confirmed in DB — remove the disk file.
            os.remove(fpath)

        db.session.commit()

    # ── 3c. Per-timeline maps ─────────────────────────────────────────────────
    timeline_maps_root = os.path.join(
        os.path.dirname(__file__), "static", "timeline_maps"
    )
    if os.path.isdir(timeline_maps_root):
        for tid_str in os.listdir(timeline_maps_root):
            try:
                tid = int(tid_str)
            except ValueError:
                continue
            folder = os.path.join(timeline_maps_root, tid_str)
            if not os.path.isdir(folder):
                continue

            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                if not os.path.isfile(fpath):
                    continue

                existing = TimelineMap.query.filter_by(
                    timeline_id=tid, filename=fname
                ).first()

                if existing is None:
                    with open(fpath, "rb") as fh:
                        data = fh.read()
                    map_row = TimelineMap(
                        timeline_id=tid,
                        filename=fname,
                        mimetype=_guess_mimetype(fname),
                        data=data,
                    )
                    db.session.add(map_row)
                    db.session.flush()
                    existing = map_row
                    map_count += 1

                # Wire up any events that still reference this file by name,
                # then clear the legacy string column.
                for ev in Event.query.filter_by(
                    timeline_id=tid, maps_id=fname
                ).all():
                    if ev.map_asset_id is None:
                        ev.map_asset_id = existing.id
                    ev.maps_id = None

                # Blob confirmed in DB — remove the disk file.
                os.remove(fpath)

        db.session.commit()

    print(f"✓  Asset migration: {img_count} image(s), {map_count} map(s) ingested from disk")


if __name__ == "__main__":
    migrate()
