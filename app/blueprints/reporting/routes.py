"""
Reporting blueprint — ReportLab PDF receipts and arrears CSV export.
"""
import io
import csv
from datetime import datetime

from flask import Blueprint, request, send_file, abort, make_response, render_template
from flask_login import login_required, current_user

from app.models import Lease, Payment
from app.blueprints.auth.routes import role_required

reporting_bp = Blueprint("reporting", __name__)


def _build_lease_agreement_pdf(lease, end_date, rent_due_day, deposit, notice_days, terms):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AgreementTitle",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=18,
        textColor=colors.HexColor("#111827"),
    )
    data = [
        ["Agreement Number", f"LA-{lease.lease_id:05d}"],
        ["Tenant", lease.tenant.email],
        ["Unit", lease.unit.unit_number],
        ["Start Date", lease.start_date.strftime("%d %B %Y")],
        ["End Date", end_date.strftime("%d %B %Y") if end_date else "Open-ended / month-to-month"],
        ["Monthly Rent", f"KES {float(lease.unit.monthly_rent):,.2f}"],
        ["Security Deposit", f"KES {float(deposit):,.2f}"],
        ["Rent Due", f"Day {rent_due_day} of each month"],
    ]
    table = Table(data, colWidths=[5 * cm, 12 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5E7EB")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#4B5563")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9CA3AF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    extra_terms = [line.strip() for line in (terms or "").splitlines() if line.strip()]
    term_paragraphs = [
        "<b>1. Premises and Term.</b> The landlord agrees to let the tenant occupy Unit "
        f"{lease.unit.unit_number} under this agreement.",
        "<b>2. Rent and Deposit.</b> Monthly rent is KES "
        f"{float(lease.unit.monthly_rent):,.2f}, payable on day {rent_due_day} of each month. "
        f"The stated security deposit is KES {float(deposit):,.2f}.",
        "<b>3. Utilities.</b> Water, trash, electricity, and other applicable utility charges "
        "shall be handled according to the property's statements and applicable Kenyan law.",
        f"<b>4. Termination.</b> Either party shall provide at least {notice_days} days' written notice.",
        "<b>5. Property Care.</b> The tenant shall keep the premises clean, avoid damage, "
        "report maintenance needs promptly, and comply with building rules.",
    ]
    for index, line in enumerate(extra_terms, start=6):
        term_paragraphs.append(f"<b>{index}. Additional Term.</b> {line}")

    elements = [
        Paragraph("MWANGAZA APARTMENTS", title_style),
        Spacer(1, 0.15 * cm),
        Paragraph("RESIDENTIAL LEASE AGREEMENT", title_style),
        Spacer(1, 0.5 * cm),
        table,
        Spacer(1, 0.5 * cm),
    ]
    for term in term_paragraphs:
        elements.append(Paragraph(term, styles["BodyText"]))
        elements.append(Spacer(1, 0.25 * cm))

    elements.extend([
        Spacer(1, 0.6 * cm),
        Table([
            ["Landlord/Caretaker Signature", "Tenant Signature"],
            ["____________________________", "____________________________"],
            [f"Date: {'_' * 18}", f"Date: {'_' * 18}"],
        ], colWidths=[8.5 * cm, 8.5 * cm], style=TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEABOVE", (0, 1), (-1, 1), 0.5, colors.white),
        ])),
        Spacer(1, 0.35 * cm),
        Paragraph(
            f"Generated on {datetime.utcnow().strftime('%d %B %Y %H:%M UTC')} "
            "for record preparation. Review and sign according to applicable law.",
            styles["Italic"],
        ),
    ])

    doc.build(elements)
    buffer.seek(0)
    return buffer

@reporting_bp.route("/lease/<int:lease_id>/agreement", methods=["GET", "POST"])
@login_required
@role_required("Landlord", "Caretaker")
def lease_agreement(lease_id):
    lease = Lease.query.get_or_404(lease_id)

    if request.method == "GET":
        return render_template(
            "lease_agreement_form.html",
            lease=lease,
        )

    end_date = request.form.get("end_date", "").strip()
    end_date_obj = None
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            abort(400, description="Invalid agreement end date.")

    try:
        deposit = float(request.form.get("deposit", lease.unit.deposit or lease.unit.monthly_rent))
        notice_days = int(request.form.get("notice_days", "30"))
        rent_due_day = int(request.form.get("rent_due_day", "1"))
    except (TypeError, ValueError):
        abort(400, description="Invalid agreement details.")

    if notice_days < 0 or not 1 <= rent_due_day <= 31:
        abort(400, description="Invalid notice or rent due day.")

    return send_file(
        _build_lease_agreement_pdf(
            lease=lease,
            end_date=end_date_obj,
            rent_due_day=str(rent_due_day),
            deposit=deposit,
            notice_days=str(notice_days),
            terms=request.form.get("terms", "").strip(),
        ),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"lease_agreement_unit_{lease.unit.unit_number}.pdf",
    )


@reporting_bp.route("/public/receipt/<string:mpesa_code>.pdf")
@login_required
def public_receipt_by_code(mpesa_code):
    payment = Payment.query.filter_by(mpesa_code=mpesa_code.upper()).first_or_404()
    if current_user.role_name == "Tenant" and payment.lease.tenant_user_id != current_user.user_id:
        abort(403)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("MWANGAZA APARTMENTS", styles["Title"]),
        Spacer(1, 0.4 * cm),
        Paragraph("Verified Payment Receipt", styles["Heading2"]),
        Spacer(1, 0.4 * cm),
    ]
    lease = payment.lease
    data = [
        ["M-Pesa Code", payment.mpesa_code],
        ["Receipt No", f"RCT-{payment.payment_id:05d}"],
        ["Unit", lease.unit.unit_number],
        ["Amount", f"KES {float(payment.amount):,.2f}"],
        ["Payment Date", payment.payment_date.strftime("%d %B %Y %H:%M UTC")],
        ["Verification Status", "VERIFIED"],
    ]
    table = Table(data, colWidths=[5 * cm, 9 * cm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"receipt-{payment.mpesa_code}.pdf",
    )


# ---------------------------------------------------------------------------
# PDF Receipt — accessible by Tenant (own) and Landlord/Caretaker (any)
# ---------------------------------------------------------------------------
@reporting_bp.route("/receipt/<int:payment_id>.pdf")
@login_required
def download_receipt(payment_id):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    payment = Payment.query.get_or_404(payment_id)
    lease = payment.lease

    # Tenants can only download their own receipts
    if current_user.role_name == "Tenant" and lease.tenant_user_id != current_user.user_id:
        abort(403)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=18
    )
    subtitle_style = ParagraphStyle(
        "subtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, textColor=colors.grey
    )
    right_style = ParagraphStyle(
        "right", parent=styles["Normal"], alignment=TA_RIGHT
    )

    elements = []

    # Header
    elements.append(Paragraph("MWANGAZA APARTMENTS", title_style))
    elements.append(Paragraph("P.O. Box 12345, Nairobi, Kenya | Tel: +254 700 000 000", subtitle_style))
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("<b>OFFICIAL PAYMENT RECEIPT</b>", title_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Receipt details table
    data = [
        ["Receipt No:", f"RCT-{payment.payment_id:05d}"],
        ["M-Pesa Code:", payment.mpesa_code],
        ["Tenant:", lease.tenant.email],
        ["Unit:", lease.unit.unit_number],
        ["Amount Paid:", f"KES {float(payment.amount):,.2f}"],
        ["Payment Date:", payment.payment_date.strftime("%d %B %Y %H:%M UTC")],
        ["Verified By:", payment.verified_by.email if payment.verified_by else "System"],
        ["Printed On:", datetime.utcnow().strftime("%d %B %Y %H:%M UTC")],
    ]

    table = Table(data, colWidths=[5 * cm, 12 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1 * cm))

    # Footer
    elements.append(Paragraph(
        "This is a computer-generated receipt. No signature required.",
        subtitle_style,
    ))
    elements.append(Paragraph(
        f"M-Pesa Reference: <b>{payment.mpesa_code}</b>",
        right_style,
    ))

    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"receipt_{payment.mpesa_code}.pdf",
    )


# ---------------------------------------------------------------------------
# Arrears CSV export (Landlord)
# ---------------------------------------------------------------------------
@reporting_bp.route("/arrears.csv")
@login_required
@role_required("Landlord")
def export_arrears_csv():
    active_leases = Lease.query.filter_by(active_status=True).all()
    arrears = [l for l in active_leases if l.balance > 0]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Lease ID", "Tenant Email", "Unit", "Total Charges (KES)",
        "Total Payments (KES)", "Balance Due (KES)",
    ])

    for lease in arrears:
        total_charges = sum(float(c.amount) for c in lease.charges)
        total_payments = sum(float(p.amount) for p in lease.payments)
        writer.writerow([
            lease.lease_id,
            lease.tenant.email,
            lease.unit.unit_number,
            f"{total_charges:,.2f}",
            f"{total_payments:,.2f}",
            f"{lease.balance:,.2f}",
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=arrears_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    )
    return response
