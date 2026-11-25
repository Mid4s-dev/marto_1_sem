"""
Audit blueprint — read-only forensic audit log inspection (Landlord only).
"""
from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models import AuditLog, User
from app.blueprints.auth.routes import role_required

audit_bp = Blueprint("audit", __name__, template_folder="../../templates")


@audit_bp.route("/logs")
@login_required
@role_required("Landlord")
def view_logs():
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Optional filters
    action_filter = request.args.get("action", "")
    entity_filter = request.args.get("entity", "")

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())

    if action_filter:
        query = query.filter(AuditLog.action_type == action_filter.upper())
    if entity_filter:
        query = query.filter(AuditLog.entity_affected.ilike(f"%{entity_filter}%"))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items

    return render_template(
        "landlord/audit_logs.html",
        logs=logs,
        pagination=pagination,
        action_filter=action_filter,
        entity_filter=entity_filter,
    )


@audit_bp.route("/logs/<int:log_id>")
@login_required
@role_required("Landlord")
def view_log_detail(log_id):
    log = AuditLog.query.get_or_404(log_id)
    return render_template("landlord/audit_log_detail.html", log=log)
