
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q

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
    all_complaints = Complaint.objects.all()

    # Update complaint status
    if request.method == "POST":
        complaint_id = request.POST.get("complaint_id")
        new_status = request.POST.get("new_status")

        if new_status in ["Open", "In Progress", "Resolved"]:
            Complaint.objects.filter(id=complaint_id).update(
                status=new_status
            )

        return redirect(request.get_full_path())

    # Read search and filter values
    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    priority = request.GET.get("priority", "")
    status = request.GET.get("status", "")
    department = request.GET.get("department", "")

    # Start with the newest complaints
    complaints = all_complaints.order_by("-created_at")

    # Search student names and complaint descriptions
    if search:
        complaints = complaints.filter(
            Q(student_name__icontains=search) |
            Q(description__icontains=search)
        )

    # Apply filters
    if category:
        complaints = complaints.filter(category=category)

    if priority:
        complaints = complaints.filter(priority=priority)

    if status:
        complaints = complaints.filter(status=status)

    if department:
        complaints = complaints.filter(department=department)

    # Prepare dashboard data
    context = {
        "complaints": complaints,

        # Summary statistics
        "total_complaints": all_complaints.count(),
        "open_complaints": all_complaints.filter(
            status="Open"
        ).count(),
        "duplicate_complaints": all_complaints.filter(
            is_duplicate=True
        ).count(),
        "high_priority": all_complaints.filter(
            priority="High"
        ).count(),

        # Complaint counts by category
        "category_stats": (
            all_complaints.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        ),

        # Available filter options
        "categories": all_complaints.values_list(
            "category", flat=True
        ).distinct(),

        "priorities": all_complaints.values_list(
            "priority", flat=True
        ).distinct(),

        "statuses": all_complaints.values_list(
            "status", flat=True
        ).distinct(),

        "departments": all_complaints.values_list(
            "department", flat=True
        ).distinct(),

        # Preserve selected filters
        "search": search,
        "selected_category": category,
        "selected_priority": priority,
        "selected_status": status,
        "selected_department": department,
    }

    return render(
        request,
        "complaints/dashboard.html",
        context
    )
