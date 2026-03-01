from django.shortcuts import render, get_object_or_404, redirect
from .models import Reservation, Blog, Equipment
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import json, time
from django.db.models import Q
from utils import myrange # Import myrange from root utils.py

# Helper function for new view: Calculates start_day and related date parameters
def _get_week_start_day_and_params(today):
    today_day = today.weekday()
    weekday_mark = 0
    if today_day < 5:  # Weekday
        start_day = today - timedelta(days=today_day)
        start_day_diff = 0 - today_day
    else:  # Weekend
        start_day_diff = 7 - today_day
        weekday_mark = 7 - today_day
        start_day = today + timedelta(days=weekday_mark)
        today_day -= 7  # Adjust today_day for date_diff calculation consistency
    date_diff = 4 - today_day  # Represents the end day for the view's logic
    return start_day, start_day_diff, weekday_mark, date_diff

# Helper function for new view: Gets list of daily reservations
def _get_daily_reservations_list(reservations_qs, equipment_id, username, start_day, myrange_func):
    day_list = []
    for i in range(0, 5):  # Monday to Friday
        day = start_day + timedelta(days=i)
        reservations_day = reservations_qs.filter(
            equipment_id=equipment_id, room_date=day
        ).order_by('room_start_time')
        temp_list = []
        for res in reservations_day:
            temp_list.extend(myrange_func(res.room_start_time, res.room_finish_time, 0.5))
        day_list.append(temp_list)
    return day_list

########################## C
def new(request, equipment_id):
    today = datetime.now()
    start_day, start_day_diff, weekday_mark, date_diff = _get_week_start_day_and_params(today)
    
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    reservations = Reservation.objects.all()
    # username used to be passed to _get_daily_reservations_list but wasn't actually used for filtering there
    day_list = _get_daily_reservations_list(reservations, equipment_id, request.user.username if request.user.is_authenticated else None, start_day, myrange)
    
    return render(request, 'reservation/new.html', {
        'equipment': equipment,
        'date_diff': date_diff,
        'weekday_mark': weekday_mark,
        'day_list': day_list,
        'start_day_diff': start_day_diff
    })

# Helper function for check view: Checks for reservation overlaps
def _check_reservation_overlap(reservations_qs, equipment_id, reserve_date, start_time, finish_time):
    if reservations_qs.filter(
        equipment_id=equipment_id, room_date=reserve_date,
        room_start_time__lt=finish_time,
        room_finish_time__gt=start_time
    ).exists():
        return True
    return False

# ajax 통신
@login_required
def check(request):
    equipment_id = request.POST.get('equipment_id', None)
    room_date_vr = request.POST.get('room_date', None)
    try:
        room_start_time_vr = float(request.POST.get('room_start_time', None))
        room_finish_time_vr = float(request.POST.get('room_finish_time', None))
    except (ValueError, TypeError):
        return HttpResponse(json.dumps({'message': "잘못된 시간 형식입니다.", 'check_error': 1}), content_type="application/json")

    reservations = Reservation.objects.all()
    reserve_date = datetime.strptime(room_date_vr, "%Y-%m-%d ").date()

    check_error = 0
    message = ""

    # 하루 2건 검사
    if reservations.filter(user=request.user.username, room_date=reserve_date).count() >= 2:
        message = "해당일에 이미 2건의 예약을 하셨습니다"
        check_error = 1
    elif _check_reservation_overlap(reservations, equipment_id, reserve_date, room_start_time_vr, room_finish_time_vr):
        message = "이미 예약된 시간입니다"
        check_error = 1

    context = {'message': message, 'check_error': check_error}
    return HttpResponse(json.dumps(context), content_type="application/json")

# C
@login_required
def create(request):
    equipment_id = request.GET['equipment_id']
    reserve_date = datetime.strptime(request.GET['room_date'], "%Y-%m-%d ").date()

    reservation = Reservation()
    reservation.user = request.GET['user']
    reservation.equipment = get_object_or_404(Equipment, pk=equipment_id)
    reservation.room_date= reserve_date
    reservation.room_start_time = request.GET['room_start_time']
    reservation.room_finish_time= request.GET['room_finish_time']
    reservation.pub_date = timezone.datetime.now()
    reservation.save()

    return redirect('/reservation/my')

def home(request):
    equipments = Equipment.objects.all()
    notices = Blog.objects.filter(category="공지사항").order_by('-pub_date')[:3]
    losts = Blog.objects.filter(category="분실물").order_by('-pub_date')[:3]
    msg = request.GET.get('msg', None)
    
    # Simple summary of today's reservations
    today = date.today()
    reservations_today = Reservation.objects.filter(room_date=today)
    
    return render(request, 'reservation/home.html', {
        'equipments': equipments,
        'notices': notices,
        'losts': losts,
        'msg': msg,
        'reservations_today': reservations_today
    })

# R 
def detail(request, blog_id) : 
    blog_detail = get_object_or_404(Blog, pk= blog_id)
    return render(request, 'reservation/detail.html', {'blog':blog_detail})

def index(request, category_name):
    blogs = Blog.objects.filter(category=category_name).order_by('-pub_date')
    category = category_name
    return render(request, 'reservation/index.html', {'category':category, 'blogs':blogs})

########################## U
def edit(request,reservation_id):
    reservation = get_object_or_404(Reservation, pk= reservation_id)
    min_date = datetime.now().strftime("%Y-%m-%d")
    max_date = (datetime.now() +timedelta(days=14)).strftime("%Y-%m-%d")
    return render(request, 'reservation/edit.html', {'reservation':reservation, 'min_date':min_date, 'max_date':max_date})

# U
def update(request,reservation_id):
    reservation= get_object_or_404(Reservation, pk= reservation_id)
    reservation.room_date= request.GET['room_date']
    reservation.room_start_time = request.GET['room_start_time']
    reservation.room_finish_time= request.GET['room_finish_time']
    reservation.save()

    return redirect('/reservation/my')

########################## D
def delete(request, reservation_id):
    reservation= get_object_or_404(Reservation, pk= reservation_id)
    if reservation.user == request.user.username:
        reservation.delete()
    return redirect('/reservation/my')                
    
########################## MY 예약
@login_required
def myreservation(request):
    today = date.today()
    now_time = datetime.now()
    now = now_time.hour + (now_time.minute / 60) 
    reservations = Reservation.objects.all()
    reservation_list = reservations.filter(Q(user=request.user.username, room_date__gt=today) | Q(user=request.user.username, room_date=today, room_finish_time__gte = now))
    return render(request, 'reservation/myreservation.html',{'reservation_list':reservation_list})
    