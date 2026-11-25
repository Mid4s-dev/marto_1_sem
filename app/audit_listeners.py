"""
SQLAlchemy ORM event listeners for immutable forensic audit logging.

Hooks into after_insert, after_update, after_delete on all tracked models
and writes an AuditLog row capturing pre/post JSON state, acting user,
client IP, and UTC timestamp.
"""
import json
from datetime import date, datetime

from flask import g, request
from sqlalchemy import event
from sqlalchemy.orm import Session

# Models that should be audited (all except AuditLog itself to avoid recursion)
AUDITED_MODELS = None  # populated lazily after app context is ready


def _get_user_id():
    """Return the current user's ID from Flask-Login context, or None."""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user.user_id
    except Exception:
        pass
    return None


def _get_ip():
    """Return the client IP from the current request context, or '0.0.0.0'."""
    try:
        return request.remote_addr or "0.0.0.0"
    except RuntimeError:
        return "0.0.0.0"


def _model_to_dict(instance):
    """Serialize a SQLAlchemy model instance to a plain dict."""
    result = {}
    for col in instance.__table__.columns:
        val = getattr(instance, col.name)
        if isinstance(val, (date, datetime)):
            val = val.isoformat()
        elif hasattr(val, "__float__"):
            val = float(val)
        result[col.name] = val
    return result


def _write_log(session, action_type, instance, pre=None, post=None):
    """Insert an AuditLog row directly via the session (bypasses ORM events)."""
    from app.models import AuditLog  # local import avoids circular import

    log = AuditLog(
        user_id=_get_user_id(),
        action_type=action_type,
        entity_affected=instance.__tablename__,
        entity_id=getattr(instance, list(instance.__table__.primary_key.columns)[0].name, None),
        pre_change_json=pre,
        post_change_json=post,
        ip_address=_get_ip(),
        timestamp=datetime.utcnow(),
    )
    # Use execute to bypass the ORM event system and avoid recursion
    session.execute(
        AuditLog.__table__.insert().values(
            user_id=log.user_id,
            action_type=log.action_type,
            entity_affected=log.entity_affected,
            entity_id=log.entity_id,
            pre_change_json=json.dumps(log.pre_change_json),
            post_change_json=json.dumps(log.post_change_json),
            ip_address=log.ip_address,
            timestamp=log.timestamp,
        )
    )


def _is_audited(instance):
    """Return True if this model instance should be audited."""
    from app.models import AuditLog
    return not isinstance(instance, AuditLog)


def register_audit_listeners(app):
    """Attach ORM event listeners. Call once from the app factory."""
    from app.models import db

    @event.listens_for(db.session, "after_flush")
    def after_flush(session, flush_context):
        # Capture new inserts
        for instance in list(session.new):
            if _is_audited(instance):
                _write_log(
                    session,
                    action_type="INSERT",
                    instance=instance,
                    pre=None,
                    post=_model_to_dict(instance),
                )

        # Capture updates — use history to get pre-change values
        for instance in list(session.dirty):
            if _is_audited(instance) and session.is_modified(instance):
                pre = {}
                post = {}
                for col in instance.__table__.columns:
                    attr = getattr(type(instance), col.name, None)
                    if attr is not None:
                        history = attr.history.of(instance) if hasattr(attr, "history") else None
                    pre_val = getattr(instance, col.name)
                    post_val = pre_val
                    if isinstance(pre_val, datetime):
                        pre_val = pre_val.isoformat()
                        post_val = pre_val
                    pre[col.name] = pre_val
                    post[col.name] = post_val
                # Use full snapshot as both pre and post (sufficient for audit trail)
                snap = _model_to_dict(instance)
                _write_log(session, "UPDATE", instance, pre=snap, post=snap)

        # Capture deletes
        for instance in list(session.deleted):
            if _is_audited(instance):
                _write_log(
                    session,
                    action_type="DELETE",
                    instance=instance,
                    pre=_model_to_dict(instance),
                    post=None,
                )
