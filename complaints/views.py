from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count

from .models import Complaint
from .ml import (
    predict_category_with_confidence,
    predict_priority,
    detect_duplicate,
    detect_language
)


def home(request):
    result = None

    if request.method == "POST":
        student_name = request.POST.get("student_name")
        description = request.POST.get("description")

        if student_name and description:
            language = detect_language(description)
            category, confidence = predict_category_with_confidence(description)
            priority = predict_priority(description)
            duplicate = detect_duplicate(description)

            departments = {
                "IT & Wi-Fi": "IT Department",
                "Hostel": "Hostel Management",
                "Academic": "Academic Office",
                "Infrastructure": "Maintenance",
                "Transport": "Transport Office"
            }

            department = departments.get(category, "Administration")

            Complaint.objects.create(
                student_name=student_name,
                description=description,
                category=category,
                priority=priority,
                department=department,
                is_duplicate=duplicate,
                language=language,
                confidence=confidence
            )

            result = {
                "category": category,
                "confidence": round(confidence * 100, 1),
                "priority": priority,
                "department": department,
                "duplicate": duplicate,
                "language": language
            }

    return render(request, "complaints/home.html", {"result": result})


@staff_member_required
def dashboard(request):
    complaints = Complaint.objects.all().order_by("-created_at")

    context = {
        "complaints": complaints,
        "total_complaints": complaints.count(),
        "open_complaints": complaints.filter(status="Open").count(),
        "duplicate_complaints": complaints.filter(is_duplicate=True).count(),
        "high_priority": complaints.filter(priority="High").count(),
        "category_stats": (
            complaints.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        ),
    }

    return render(request, "complaints/dashboard.html", context)