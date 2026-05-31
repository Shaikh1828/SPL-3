"""
Report generation service for PDF, CSV, and JSON export.

Story coverage: US-4.1 (generate tournament reports)
"""

import os
import csv
import json
from datetime import datetime
from typing import Optional, Literal
from io import BytesIO, StringIO
from sqlalchemy.orm import Session
import structlog

from src.models.tournament import Session as SessionModel
from src.models.scoring import SessionArcher, Score
from src.config import settings

logger = structlog.get_logger()

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
except ImportError:
    logger.warning("reportlab_not_available")


class ReportService:
    """Report generation service."""

    @staticmethod
    def generate_report(
        db: Session,
        session_id: int,
        format: Literal["pdf", "csv", "json"] = "pdf",
    ) -> bytes:
        """
        Generate report in specified format.

        Args:
            db: Database session
            session_id: Session ID
            format: Report format (pdf, csv, json)

        Returns:
            Report as bytes

        Raises:
            ValueError: If format not supported
        """
        if format == "pdf":
            return ReportService._generate_pdf_report(db, session_id)
        elif format == "csv":
            return ReportService._generate_csv_report(db, session_id)
        elif format == "json":
            return ReportService._generate_json_report(db, session_id)
        else:
            raise ValueError(f"Unsupported report format: {format}")

    @staticmethod
    def _generate_pdf_report(db: Session, session_id: int) -> bytes:
        """Generate PDF report (requires reportlab)."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        try:
            # Create PDF in memory
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []

            # Title
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1f77b4"),
                spaceAfter=30,
            )
            elements.append(Paragraph(f"Tournament Report - {session.name}", title_style))
            elements.append(Spacer(1, 0.2 * inch))

            # Session info
            session_info = f"<b>Tournament:</b> {session.tournament.name}<br/>" \
                          f"<b>Location:</b> {session.tournament.location}<br/>" \
                          f"<b>Session:</b> {session.name}<br/>" \
                          f"<b>Status:</b> {session.status}<br/>" \
                          f"<b>Generated:</b> {datetime.utcnow().isoformat()}"
            elements.append(Paragraph(session_info, styles["Normal"]))
            elements.append(Spacer(1, 0.3 * inch))

            # Leaderboard table
            elements.append(Paragraph("<b>Leaderboard</b>", styles["Heading2"]))
            leaderboard_data = [["Rank", "Archer", "Total Score", "Round"]]

            archers = (
                db.query(SessionArcher)
                .filter(SessionArcher.session_id == session_id)
                .order_by(SessionArcher.total_score.desc())
                .all()
            )

            for rank, archer in enumerate(archers, 1):
                leaderboard_data.append(
                    [str(rank), archer.archer_name, str(archer.total_score), str(archer.current_round)]
                )

            table = Table(leaderboard_data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            elements.append(table)

            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            return buffer.read()

        except Exception as e:
            logger.exception("pdf_generation_error", error=str(e))
            raise

    @staticmethod
    def _generate_csv_report(db: Session, session_id: int) -> bytes:
        """Generate CSV report."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        try:
            output = StringIO()
            writer = csv.writer(output)

            # Header
            writer.writerow([
                "Session ID", "Session Name", "Tournament", "Location",
                "Status", "Generated"
            ])
            writer.writerow([
                session.id, session.name, session.tournament.name,
                session.tournament.location, session.status, datetime.utcnow().isoformat()
            ])
            writer.writerow([])

            # Leaderboard
            writer.writerow(["Rank", "Archer Name", "Archer ID", "Total Score", "Current Round"])

            archers = (
                db.query(SessionArcher)
                .filter(SessionArcher.session_id == session_id)
                .order_by(SessionArcher.total_score.desc())
                .all()
            )

            for rank, archer in enumerate(archers, 1):
                writer.writerow([
                    rank, archer.archer_name, archer.archer_id,
                    archer.total_score, archer.current_round
                ])

            return output.getvalue().encode("utf-8")

        except Exception as e:
            logger.exception("csv_generation_error", error=str(e))
            raise

    @staticmethod
    def _generate_json_report(db: Session, session_id: int) -> bytes:
        """Generate JSON report."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        try:
            # Query data
            archers = (
                db.query(SessionArcher)
                .filter(SessionArcher.session_id == session_id)
                .order_by(SessionArcher.total_score.desc())
                .all()
            )

            # Build report structure
            report = {
                "session": {
                    "id": session.id,
                    "name": session.name,
                    "status": session.status,
                    "tournament": {
                        "name": session.tournament.name,
                        "location": session.tournament.location,
                    },
                },
                "generated": datetime.utcnow().isoformat(),
                "leaderboard": [
                    {
                        "rank": rank,
                        "archer_name": archer.archer_name,
                        "archer_id": archer.archer_id,
                        "total_score": archer.total_score,
                        "current_round": archer.current_round,
                    }
                    for rank, archer in enumerate(archers, 1)
                ],
            }

            return json.dumps(report, indent=2).encode("utf-8")

        except Exception as e:
            logger.exception("json_generation_error", error=str(e))
            raise

    @staticmethod
    def save_report(report_bytes: bytes, session_id: int, format: str) -> str:
        """
        Save report to disk.

        Args:
            report_bytes: Report content as bytes
            session_id: Session ID
            format: Report format (pdf, csv, json)

        Returns:
            Path to saved report
        """
        reports_dir = os.path.join(settings.storage_path, "reports", str(session_id))
        os.makedirs(reports_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.{format}"
        filepath = os.path.join(reports_dir, filename)

        with open(filepath, "wb") as f:
            f.write(report_bytes)

        logger.info("report_saved", filepath=filepath, format=format)

        return filepath
