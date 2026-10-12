import math
import io
import csv
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse

from app.services.dissertation_export import (
    RESEARCH_DATA,
    generate_dissertation_docx,
    generate_dissertation_excel
)

router = APIRouter(prefix="/research", tags=["Tadqiqotchi"])


@router.get("/tables")
def get_all_dissertation_tables(institution: Optional[str] = Query(None)):
    """
    Dissertatsiya 4-bobi uchun barcha statistik jadvallar (4.2, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9).
    """
    data = dict(RESEARCH_DATA)
    if institution and institution != "all":
        # Filtr bo'yicha ko'rsatish
        data["filter_applied"] = institution
    return data


@router.get("/baseline-equivalence")
def get_baseline_equivalence():
    """
    Tajriba va nazorat guruhlarining boshlang'ich tenglik tekshiruvi (Chi-square).
    """
    return {
        "metric": "Pearson Chi-Square",
        "sample_sizes": {
            "experimental_group": 132,
            "control_group": 126,
            "total": 258,
            "primary_base_buxdu": {"exp": 46, "ctrl": 44, "total": 90}
        },
        "chi_square_value": 0.45,
        "degrees_of_freedom": 2,
        "p_value": 0.798,
        "interpretation": "p > 0.05. Guruhlarning dastlabki CEFR darajalari statistik jihatdan teng va farqsiz ekani to'liq isbotlandi.",
        "equivalence_confirmed": True
    }


@router.get("/statistics")
def get_research_statistics():
    """
    Dissertatsiya 4-bobi uchun zarur asosiy ilmiy ko'rsatkichlar.
    """
    exp_pre_mean = 54.1
    exp_post_mean = 78.5
    ctrl_pre_mean = 53.6
    ctrl_post_mean = 64.2
    
    return {
        "groups": {
            "experimental": {
                "name": "Tajriba guruhi (Tabaqalashtirilgan adaptiv-metakognitiv model)",
                "sample_size": 132,
                "pre_test_mean": exp_pre_mean,
                "post_test_mean": exp_post_mean,
                "growth_percentage": "+45.1%",
                "t_statistic": 24.32,
                "p_value": "< 0.001"
            },
            "control": {
                "name": "Nazorat guruhi (An'anaviy ta'lim)",
                "sample_size": 126,
                "pre_test_mean": ctrl_pre_mean,
                "post_test_mean": ctrl_post_mean,
                "growth_percentage": "+19.8%",
                "t_statistic": 9.15,
                "p_value": "< 0.001"
            }
        },
        "effect_size": {
            "cohens_d": 1.66,
            "magnitude": "Katta effekt (Large Effect > 0.8)",
            "significance": "Tabaqalashtirilgan adaptiv-metakognitiv model an'anaviy yondashuvdan statistik ishonchli darajada yuqori samaradorlik ko'rsatdi."
        },
        "coefficients": {
            "mastery_rate_exp": 0.81,
            "mastery_rate_ctrl": 0.64,
            "effectiveness_ratio": 1.26,
            "superiority_percentage": "+26.1%"
        }
    }


@router.get("/export-docx")
def export_docx():
    """
    Dissertatsiyaga to'g'ridan-to'g'ri kiritish uchun 4-bob jadvallarini Word (.docx) formatida yuklab berish.
    """
    file_stream = generate_dissertation_docx()
    filename = "TILORA_Dissertatsiya_4_Bob_Jadvallari.docx"
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export-excel")
def export_excel():
    """
    Dissertatsiyaning 4-bobi uchun barcha jadvallarni Excel (.xlsx) kitobida yuklab berish.
    """
    file_stream = generate_dissertation_excel()
    filename = "TILORA_Dissertatsiya_4_Bob_Statistika.xlsx"
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export-csv")
def export_csv():
    """
    CSV formatida yuklab berish.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["OTM", "Guruh", "Pre-test", "Post-test", "O'sish", "t-mezon", "p-qiymat", "Bespalko K"])
    for r in RESEARCH_DATA["table_4_5"]["rows"]:
        writer.writerow([r["institution"], "Tajriba", r["exp_pre"], r["exp_post"], r["exp_growth"], r["exp_t"], "< 0.001", "0.81"])
        writer.writerow([r["institution"], "Nazorat", r["ctrl_pre"], r["ctrl_post"], r["ctrl_growth"], r["ctrl_t"], "< 0.001", "0.64"])
    
    csv_bytes = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    output.close()
    filename = "TILORA_Dissertatsiya_Statistika.csv"
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export")
def export_research_data(format: str = "docx"):
    if format == "excel" or format == "xlsx":
        return export_excel()
    elif format == "csv":
        return export_csv()
    return export_docx()
