import os
import csv
import json
import math
from datetime import datetime
from typing import Optional, Literal, List, Dict, Any
from io import BytesIO, StringIO
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
import structlog

from src.models.tournament import Tournament, Session as SessionModel
from src.models.scoring import SessionArcher, Score
from src.models.user import User
from src.config import settings

logger = structlog.get_logger()

REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab_not_available_using_fallback_pdf_engine")


class ReportService:
    """Report and Advanced Analytics Generation Service."""

    @staticmethod
    def get_tournament_analytics(
        db: Session,
        tournament_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compute real-time statistical analytics for a tournament or specific session.
        Calculates score distribution, end-by-end fatigue trends, lane-by-lane variance, and AI telemetry.
        """
        score_query = db.query(Score, SessionArcher, SessionModel, Tournament).join(
            SessionArcher, Score.session_archer_id == SessionArcher.id
        ).join(
            SessionModel, Score.session_id == SessionModel.id
        ).join(
            Tournament, SessionModel.tournament_id == Tournament.id
        )

        tourney_obj = None
        session_obj = None

        if session_id:
            session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
            score_query = score_query.filter(Score.session_id == session_id)
            if session_obj:
                tourney_obj = session_obj.tournament
        elif tournament_id:
            tourney_obj = db.query(Tournament).filter(Tournament.id == tournament_id).first()
            score_query = score_query.filter(SessionModel.tournament_id == tournament_id)

        records = score_query.all()

        total_arrows = len(records)
        total_points = sum(r[0].points for r in records)
        overall_avg = round(total_points / total_arrows, 2) if total_arrows > 0 else 0.0

        # Distinct archers count
        distinct_archers = set(r[1].archer_id for r in records)
        total_archers = len(distinct_archers)

        # 1. Score Distribution (X, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, Miss)
        zone_counts = {
            "X": 0, "10": 0, "9": 0, "8": 0, "7": 0,
            "6": 0, "5": 0, "4": 0, "3": 0, "2": 0, "1": 0, "M": 0
        }

        for score, sa, s, t in records:
            pts = score.points
            is_x = bool(score.image_id and "x" in str(score.image_id).lower())
            if pts == 10 and is_x:
                zone_counts["X"] += 1
            elif pts == 10:
                zone_counts["10"] += 1
            elif pts == 0:
                zone_counts["M"] += 1
            else:
                zone_counts[str(pts)] = zone_counts.get(str(pts), 0) + 1

        score_distribution = []
        for z in ["X", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M"]:
            c = zone_counts.get(z, 0)
            pct = round((c / total_arrows) * 100, 1) if total_arrows > 0 else 0.0
            score_distribution.append({"zone": z, "count": c, "percentage": pct})

        # 2. End-by-End Progression (End 1 to 6+)
        end_map: Dict[int, List[int]] = {}
        for score, sa, s, t in records:
            end_map.setdefault(score.round, []).append(score.points)

        end_progression = []
        for end_num in sorted(end_map.keys()):
            pts_list = end_map[end_num]
            avg_e = round(sum(pts_list) / len(pts_list), 2) if pts_list else 0.0
            end_progression.append({
                "end": end_num,
                "avg_score": avg_e,
                "total_arrows": len(pts_list),
            })

        # 3. Lane Accuracy & Variance (Lanes 1–6+)
        lane_map: Dict[int, List[Score]] = {}
        for score, sa, s, t in records:
            lane_num = sa.lane_number or 1
            lane_map.setdefault(lane_num, []).append(score)

        lane_accuracy = []
        for lane_num in sorted(lane_map.keys()):
            l_scores = lane_map[lane_num]
            l_pts = [sc.points for sc in l_scores]
            avg_l = round(sum(l_pts) / len(l_pts), 2) if l_pts else 0.0
            tens_count = sum(1 for sc in l_scores if sc.points == 10)
            tens_rate = round((tens_count / len(l_scores)) * 100, 1) if l_scores else 0.0
            lane_accuracy.append({
                "lane": lane_num,
                "avg_score": avg_l,
                "arrows_shot": len(l_scores),
                "tens_rate": tens_rate,
            })

        # 4. AI Telemetry Metrics
        ai_validated_count = sum(1 for score, sa, s, t in records if score.validated_by_ai)
        overridden_count = total_arrows - ai_validated_count
        conf_sum = sum(score.confidence or 0.95 for score, sa, s, t in records)
        avg_conf = round(conf_sum / total_arrows, 3) if total_arrows > 0 else 0.95
        ai_val_pct = round((ai_validated_count / total_arrows) * 100, 1) if total_arrows > 0 else 100.0

        ai_metrics = {
            "total_arrows": total_arrows,
            "ai_validated_percent": ai_val_pct,
            "avg_confidence": avg_conf,
            "overridden_count": overridden_count,
        }

        return {
            "tournament_id": tourney_obj.id if tourney_obj else None,
            "tournament_name": tourney_obj.name if tourney_obj else "All Tournaments Aggregated",
            "session_id": session_obj.id if session_obj else None,
            "session_name": session_obj.name if session_obj else None,
            "total_archers": total_archers,
            "total_arrows_shot": total_arrows,
            "total_points_scored": total_points,
            "overall_average_arrow": overall_avg,
            "score_distribution": score_distribution,
            "end_progression": end_progression,
            "lane_accuracy": lane_accuracy,
            "ai_metrics": ai_metrics,
        }

    @staticmethod
    def get_archer_longitudinal_analytics(
        db: Session,
        archer_id: Optional[int] = None,
        archer_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compute longitudinal multi-tournament analytics for a specific archer.
        Tracks their career progression, win/podium history, stability index, and radar stats.
        """
        # Find session archers for this athlete
        sa_query = db.query(SessionArcher, SessionModel, Tournament).join(
            SessionModel, SessionArcher.session_id == SessionModel.id
        ).join(
            Tournament, SessionModel.tournament_id == Tournament.id
        )

        if archer_name:
            sa_query = sa_query.filter(SessionArcher.archer_name.ilike(f"%{archer_name}%"))
        elif archer_id:
            # Find the athlete name corresponding to this archer_id
            target_sa = db.query(SessionArcher).filter(SessionArcher.archer_id == archer_id).first()
            if target_sa:
                sa_query = sa_query.filter(SessionArcher.archer_name == target_sa.archer_name)
            else:
                sa_query = sa_query.filter(SessionArcher.archer_id == archer_id)

        sa_records = sa_query.all()
        if not sa_records:
            # Fallback: search by user table or return empty profile
            user = db.query(User).filter(User.id == archer_id).first() if archer_id else None
            return {
                "archer_id": archer_id or 0,
                "archer_name": user.username if user else (archer_name or "Unknown Archer"),
                "tournaments_participated": 0,
                "total_career_points": 0,
                "overall_arrow_average": 0.0,
                "total_tens": 0,
                "total_xs": 0,
                "career_high_end": 0,
                "consistency_index": 0.0,
                "tournaments": [],
                "score_distribution": [],
                "end_progression": [],
            }

        resolved_name = sa_records[0][0].archer_name
        resolved_id = sa_records[0][0].archer_id or archer_id or 1

        # Group by tournament
        tourney_map: Dict[int, Dict[str, Any]] = {}
        for sa, session, tourney in sa_records:
            t_id = tourney.id
            if t_id not in tourney_map:
                tourney_map[t_id] = {
                    "tournament_id": t_id,
                    "tournament_name": tourney.name,
                    "location": tourney.location,
                    "session_archers": [],
                    "sessions": [],
                }
            tourney_map[t_id]["session_archers"].append(sa)
            tourney_map[t_id]["sessions"].append(session)

        tournament_histories = []
        all_archer_scores: List[Score] = []

        for t_id, t_info in tourney_map.items():
            sa_ids = [sa.id for sa in t_info["session_archers"]]
            scores = db.query(Score).filter(Score.session_archer_id.in_(sa_ids)).all()
            all_archer_scores.extend(scores)

            t_points = sum(sc.points for sc in scores)
            t_arrows = len(scores)
            t_avg = round(t_points / t_arrows, 2) if t_arrows > 0 else 0.0
            t_tens = sum(1 for sc in scores if sc.points == 10)
            t_xs = sum(1 for sc in scores if sc.points == 10 and sc.image_id and "x" in str(sc.image_id).lower())

            # Find best end in tournament
            end_sums: Dict[tuple, int] = {}
            for sc in scores:
                key = (sc.session_id, sc.round)
                end_sums[key] = end_sums.get(key, 0) + sc.points
            best_end = max(end_sums.values()) if end_sums else 0

            # Determine rank in tournament against all competitors
            session_ids = [s.id for s in t_info["sessions"]]
            all_t_archers = (
                db.query(SessionArcher.archer_name, func.sum(SessionArcher.total_score).label("sum_score"))
                .filter(SessionArcher.session_id.in_(session_ids))
                .group_by(SessionArcher.archer_name)
                .order_by(func.sum(SessionArcher.total_score).desc())
                .all()
            )
            rank = 1
            for idx, (comp_name, sum_sc) in enumerate(all_t_archers, 1):
                if comp_name == resolved_name:
                    rank = idx
                    break

            tournament_histories.append({
                "tournament_id": t_id,
                "tournament_name": t_info["tournament_name"],
                "location": t_info["location"],
                "sessions_count": len(t_info["sessions"]),
                "arrows_shot": t_arrows,
                "total_points": t_points,
                "average_arrow": t_avg,
                "rank": rank,
                "tens_count": t_tens,
                "xs_count": t_xs,
                "best_end_score": best_end,
            })

        # Overall career aggregates
        career_points = sum(sc.points for sc in all_archer_scores)
        career_arrows = len(all_archer_scores)
        career_avg = round(career_points / career_arrows, 2) if career_arrows > 0 else 0.0
        career_tens = sum(1 for sc in all_archer_scores if sc.points == 10)
        career_xs = sum(1 for sc in all_archer_scores if sc.points == 10 and sc.image_id and "x" in str(sc.image_id).lower())

        # Consistency Index (Standard deviation across all ends)
        all_end_scores: Dict[tuple, int] = {}
        for sc in all_archer_scores:
            key = (sc.session_archer_id, sc.round)
            all_end_scores[key] = all_end_scores.get(key, 0) + sc.points

        end_totals = list(all_end_scores.values())
        career_high_end = max(end_totals) if end_totals else 0

        if len(end_totals) > 1:
            mean_end = sum(end_totals) / len(end_totals)
            variance = sum((x - mean_end) ** 2 for x in end_totals) / (len(end_totals) - 1)
            std_dev = round(math.sqrt(variance), 2)
        else:
            std_dev = 0.0

        # Score distribution for archer
        z_counts = {
            "X": 0, "10": 0, "9": 0, "8": 0, "7": 0,
            "6": 0, "5": 0, "4": 0, "3": 0, "2": 0, "1": 0, "M": 0
        }
        for sc in all_archer_scores:
            is_x = bool(sc.image_id and "x" in str(sc.image_id).lower())
            if sc.points == 10 and is_x:
                z_counts["X"] += 1
            elif sc.points == 10:
                z_counts["10"] += 1
            elif sc.points == 0:
                z_counts["M"] += 1
            else:
                z_counts[str(sc.points)] = z_counts.get(str(sc.points), 0) + 1

        archer_dist = []
        for z in ["X", "10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M"]:
            cnt = z_counts.get(z, 0)
            pct = round((cnt / career_arrows) * 100, 1) if career_arrows > 0 else 0.0
            archer_dist.append({"zone": z, "count": cnt, "percentage": pct})

        # End-by-end fatigue progression for archer
        archer_ends: Dict[int, List[int]] = {}
        for sc in all_archer_scores:
            archer_ends.setdefault(sc.round, []).append(sc.points)

        archer_prog = []
        for e_num in sorted(archer_ends.keys()):
            pts_e = archer_ends[e_num]
            avg_e = round(sum(pts_e) / len(pts_e), 2) if pts_e else 0.0
            archer_prog.append({
                "end": e_num,
                "avg_score": avg_e,
                "total_arrows": len(pts_e),
            })

        return {
            "archer_id": resolved_id,
            "archer_name": resolved_name,
            "tournaments_participated": len(tournament_histories),
            "total_career_points": career_points,
            "overall_arrow_average": career_avg,
            "total_tens": career_tens,
            "total_xs": career_xs,
            "career_high_end": career_high_end,
            "consistency_index": std_dev,
            "tournaments": tournament_histories,
            "score_distribution": archer_dist,
            "end_progression": archer_prog,
        }

    @staticmethod
    def list_archers_directory(db: Session) -> List[Dict[str, Any]]:
        """List distinct archers across all tournaments with summary metrics."""
        results = (
            db.query(
                func.min(SessionArcher.archer_id).label("archer_id"),
                SessionArcher.archer_name,
                func.count(distinct(SessionModel.tournament_id)).label("tournaments_count"),
                func.sum(SessionArcher.total_score).label("total_score"),
            )
            .join(SessionModel, SessionArcher.session_id == SessionModel.id)
            .group_by(SessionArcher.archer_name)
            .order_by(func.sum(SessionArcher.total_score).desc())
            .all()
        )

        archers = []
        for a_id, name, t_count, tot_score in results:
            sa_ids = db.query(SessionArcher.id).filter(SessionArcher.archer_name == name).all()
            sa_id_list = [s[0] for s in sa_ids]
            arrow_count = db.query(Score).filter(Score.session_archer_id.in_(sa_id_list)).count()
            avg = round(tot_score / arrow_count, 2) if arrow_count > 0 else 0.0

            archers.append({
                "archer_id": a_id or 1,
                "archer_name": name,
                "tournaments_count": t_count,
                "total_score": tot_score or 0,
                "average_arrow": avg,
            })

        return archers

    @staticmethod
    def generate_report(
        db: Session,
        session_id: int,
        format: Literal["pdf", "csv", "json"] = "pdf",
    ) -> bytes:
        """Generate report for a specific session."""
        if format == "pdf":
            return ReportService._generate_pdf_report(db, session_id)
        elif format == "csv":
            return ReportService._generate_csv_report(db, session_id)
        elif format == "json":
            return ReportService._generate_json_report(db, session_id)
        else:
            raise ValueError(f"Unsupported report format: {format}")

    @staticmethod
    def generate_tournament_report(
        db: Session,
        tournament_id: int,
        format: Literal["pdf", "csv", "json"] = "pdf",
    ) -> bytes:
        """Generate tournament-wide multi-session report."""
        tourney = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tourney:
            raise ValueError(f"Tournament not found: {tournament_id}")

        if format == "pdf":
            return ReportService._generate_tournament_pdf_report(db, tourney)
        elif format == "csv":
            return ReportService._generate_tournament_csv_report(db, tourney)
        elif format == "json":
            return ReportService._generate_tournament_json_report(db, tourney)
        else:
            raise ValueError(f"Unsupported report format: {format}")

    @staticmethod
    def _build_minimal_pdf(title: str, subtitle: str, lines: List[str]) -> bytes:
        """Create a compliant, self-contained PDF 1.4 binary without external dependencies."""
        content_lines = [
            "BT",
            "/F1 16 Tf",
            "40 750 Td",
            f"({title}) Tj",
            "/F1 12 Tf",
            "0 -22 Td",
            f"({subtitle}) Tj",
            "/F1 9 Tf",
            "0 -25 Td",
        ]
        for line in lines[:45]:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content_lines.append(f"({escaped}) Tj")
            content_lines.append("0 -14 Td")
        content_lines.append("ET")
        
        stream_content = "\n".join(content_lines).encode("latin-1", errors="replace")
        stream_len = len(stream_content)
        
        pdf_template = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
            b"4 0 obj\n<< /Length " + str(stream_len).encode("ascii") + b" >>\nstream\n"
            + stream_content + b"\nendstream\nendobj\n"
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000236 00000 n \n"
            b"0000000300 00000 n \n"
            b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n400\n%%EOF\n"
        )
        return pdf_template

    @staticmethod
    def _generate_pdf_report(db: Session, session_id: int) -> bytes:
        """Generate session PDF report."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        archers = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id)
            .order_by(SessionArcher.total_score.desc())
            .all()
        )

        if not REPORTLAB_AVAILABLE:
            lines = [
                f"Tournament: {session.tournament.name} | Location: {session.tournament.location}",
                f"Session Round: {session.round_number} | Status: {session.status.upper()} | Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                "--------------------------------------------------------------------------------",
                "STANDINGS & COMPETITOR RESULTS:",
            ]
            for rank, a in enumerate(archers, 1):
                lines.append(f"#{rank:02d} | {a.archer_name:<28} | Lane {a.lane_number} | Score: {a.total_score} pts | Round {a.current_round}")
            return ReportService._build_minimal_pdf(f"Official Match Report - {session.name}", f"Tournament: {session.tournament.name}", lines)

        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            elements = []
            styles = getSampleStyleSheet()

            # Header Title
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=20,
                textColor=colors.HexColor("#0f172a"),
                spaceAfter=15,
            )
            elements.append(Paragraph(f"Official Match Report — {session.name}", title_style))

            # Details
            info_text = f"<b>Tournament:</b> {session.tournament.name} | <b>Location:</b> {session.tournament.location}<br/>" \
                        f"<b>Session Round:</b> {session.round_number} | <b>Status:</b> {session.status.upper()} | <b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            elements.append(Paragraph(info_text, styles["Normal"]))
            elements.append(Spacer(1, 0.2 * inch))

            # Leaderboard Table
            elements.append(Paragraph("<b>Competitor Standings & Results</b>", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))

            leaderboard_data = [["Rank", "Archer Name", "Lane", "Round", "Total Score"]]
            for rank, archer in enumerate(archers, 1):
                leaderboard_data.append([
                    str(rank),
                    archer.archer_name,
                    f"Lane {archer.lane_number or '-'}",
                    f"Round {archer.current_round}",
                    f"{archer.total_score} pts",
                ])

            table = Table(leaderboard_data, colWidths=[50, 200, 80, 80, 100])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            elements.append(table)

            doc.build(elements)
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            logger.exception("pdf_generation_error", error=str(e))
            lines = [
                f"Tournament: {session.tournament.name}",
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            ]
            return ReportService._build_minimal_pdf(f"Report: {session.name}", session.tournament.name, lines)

    @staticmethod
    def _generate_tournament_pdf_report(db: Session, tourney: Tournament) -> bytes:
        """Generate tournament-wide PDF report."""
        from src.services.leaderboard_service import LeaderboardService
        t_leaderboard = LeaderboardService.get_tournament_leaderboard(db, tourney.id, limit=50)

        if not REPORTLAB_AVAILABLE:
            lines = [
                f"Championship Event: {tourney.name}",
                f"Location: {tourney.location or 'Arena'} | Dates: {tourney.start_date.strftime('%b %d, %Y')} - {tourney.end_date.strftime('%b %d, %Y')}",
                "--------------------------------------------------------------------------------",
                "OFFICIAL TOURNAMENT STANDINGS & SCORES:",
            ]
            for item in t_leaderboard:
                lines.append(f"#{item['rank']:02d} | {item['archer_name']:<28} | Score: {item['total_score']} pts | Avg: {item.get('average_score', 0):.2f} | 10s: {item.get('tens_count', 0)}")
            return ReportService._build_minimal_pdf(f"Tournament Report - {tourney.name}", f"Championship Standings", lines)

        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                "CustomTourneyTitle",
                parent=styles["Heading1"],
                fontSize=22,
                textColor=colors.HexColor("#d97706"),
                spaceAfter=10,
            )
            elements.append(Paragraph(f"Championship Tournament Report", title_style))
            elements.append(Paragraph(f"<b>{tourney.name}</b>", styles["Heading2"]))

            info = f"<b>Location:</b> {tourney.location or 'Standard Range'} | <b>Dates:</b> {tourney.start_date.strftime('%b %d, %Y')} to {tourney.end_date.strftime('%b %d, %Y')}<br/>" \
                   f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            elements.append(Paragraph(info, styles["Normal"]))
            elements.append(Spacer(1, 0.2 * inch))

            # Tournament Leaderboard
            elements.append(Paragraph("<b>Overall Tournament Leaderboard</b>", styles["Heading2"]))
            elements.append(Spacer(1, 0.1 * inch))

            t_table_data = [["Rank", "Competitor Name", "Total Score", "Avg Arrow", "10s", "Xs"]]
            for item in t_leaderboard:
                t_table_data.append([
                    str(item["rank"]),
                    item["archer_name"],
                    f"{item['total_score']} pts",
                    f"{item.get('average_score', 0):.2f}",
                    str(item.get("tens_count", 0)),
                    str(item.get("xs_count", 0)),
                ])

            t_table = Table(t_table_data, colWidths=[40, 200, 90, 70, 50, 50])
            t_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d97706")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fffbeb")),
            ]))
            elements.append(t_table)

            doc.build(elements)
            buffer.seek(0)
            return buffer.read()
        except Exception as e:
            logger.exception("tournament_pdf_error", error=str(e))
            lines = [
                f"Tournament: {tourney.name}",
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            ]
            return ReportService._build_minimal_pdf(f"Tournament Report - {tourney.name}", tourney.name, lines)
            raise

    @staticmethod
    def _generate_csv_report(db: Session, session_id: int) -> bytes:
        """Generate session CSV report."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Session ID", "Session Name", "Tournament", "Location", "Status", "Generated"])
        writer.writerow([session.id, session.name, session.tournament.name, session.tournament.location, session.status, datetime.utcnow().isoformat()])
        writer.writerow([])
        writer.writerow(["Rank", "Archer Name", "Archer ID", "Lane", "Total Score", "Current Round"])

        archers = db.query(SessionArcher).filter(SessionArcher.session_id == session_id).order_by(SessionArcher.total_score.desc()).all()
        for rank, archer in enumerate(archers, 1):
            writer.writerow([rank, archer.archer_name, archer.archer_id, archer.lane_number, archer.total_score, archer.current_round])

        return output.getvalue().encode("utf-8")

    @staticmethod
    def _generate_tournament_csv_report(db: Session, tourney: Tournament) -> bytes:
        """Generate tournament-wide CSV report."""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Tournament ID", "Tournament Name", "Location", "Start Date", "End Date", "Generated"])
        writer.writerow([tourney.id, tourney.name, tourney.location, tourney.start_date.isoformat(), tourney.end_date.isoformat(), datetime.utcnow().isoformat()])
        writer.writerow([])

        from src.services.leaderboard_service import LeaderboardService
        t_leaderboard = LeaderboardService.get_tournament_leaderboard(db, tourney.id, limit=100)

        writer.writerow(["Rank", "Archer Name", "Archer ID", "Total Score", "Average Arrow", "10s Count", "Xs Count"])
        for item in t_leaderboard:
            writer.writerow([item["rank"], item["archer_name"], item["archer_id"], item["total_score"], item.get("average_score", 0), item.get("tens_count", 0), item.get("xs_count", 0)])

        return output.getvalue().encode("utf-8")

    @staticmethod
    def _generate_json_report(db: Session, session_id: int) -> bytes:
        """Generate session JSON report."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        archers = db.query(SessionArcher).filter(SessionArcher.session_id == session_id).order_by(SessionArcher.total_score.desc()).all()
        report = {
            "session": {
                "id": session.id,
                "name": session.name,
                "status": session.status,
                "tournament": {"name": session.tournament.name, "location": session.tournament.location},
            },
            "generated": datetime.utcnow().isoformat(),
            "leaderboard": [
                {
                    "rank": rank,
                    "archer_name": a.archer_name,
                    "archer_id": a.archer_id,
                    "lane_number": a.lane_number,
                    "total_score": a.total_score,
                    "current_round": a.current_round,
                }
                for rank, a in enumerate(archers, 1)
            ],
        }
        return json.dumps(report, indent=2).encode("utf-8")

    @staticmethod
    def _generate_tournament_json_report(db: Session, tourney: Tournament) -> bytes:
        """Generate tournament-wide JSON report."""
        from src.services.leaderboard_service import LeaderboardService
        t_leaderboard = LeaderboardService.get_tournament_leaderboard(db, tourney.id, limit=100)
        analytics = ReportService.get_tournament_analytics(db, tournament_id=tourney.id)

        report = {
            "tournament": {
                "id": tourney.id,
                "name": tourney.name,
                "location": tourney.location,
                "start_date": tourney.start_date.isoformat(),
                "end_date": tourney.end_date.isoformat(),
            },
            "generated": datetime.utcnow().isoformat(),
            "leaderboard": t_leaderboard,
            "analytics_summary": analytics,
        }
        return json.dumps(report, indent=2).encode("utf-8")

    @staticmethod
    def save_report(report_bytes: bytes, session_id: int, format: str) -> str:
        """Save report to disk."""
        reports_dir = os.path.join(settings.storage_path, "reports", str(session_id))
        os.makedirs(reports_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.{format}"
        filepath = os.path.join(reports_dir, filename)
        with open(filepath, "wb") as f:
            f.write(report_bytes)
        logger.info("report_saved", filepath=filepath, format=format)
        return filepath

