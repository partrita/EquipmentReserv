from django.shortcuts import render, get_object_or_404, redirect
from .models import Reservation, Blog
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
def _get_daily_reservations_list(reservations_qs, room_type, username, start_day, myrange_func):
    day_list = []
    for i in range(0, 5):  # Monday to Friday
        day = start_day + timedelta(days=i)
        reservations_day = reservations_qs.filter(
            room_type=room_type, user=username, room_date=day
        ).order_by('room_start_time')
        temp_list = []
        for res in reservations_day:
            temp_list.extend(myrange_func(res.room_start_time, res.room_finish_time, 0.5))
        day_list.append(temp_list)
    return day_list

########################## C
@login_required
def new(request,room_type):
    today =  datetime.now()
    start_day, start_day_diff, weekday_mark, date_diff = _get_week_start_day_and_params(today)

    reservations = Reservation.objects.all() # Consider filtering further if possible for performance
    day_list = _get_daily_reservations_list(reservations, room_type, request.user.username, start_day, myrange)
    
    return render(request, 'reservation/new.html', {
        'room_type':room_type,
        'date_diff':date_diff,
        'weekday_mark':weekday_mark,
        'day_list':day_list,
        'start_day_diff':start_day_diff
    })

# Helper function for check view: Checks for reservation overlaps
def _check_reservation_overlap(reservations_qs, room_type, reserve_date, start_time, finish_time):
    # Convert times to float if they are not already, assuming model fields are FloatField
    # In this case, room_start_time_vr and room_finish_time_vr are already strings from POST
    # and Django's ORM can handle string-to-float conversion for lookups if needed,
    # but it's safer to ensure types match model field types.
    # However, the existing code uses them directly in filters, implying they are treated as numbers by the ORM.
    # For direct comparison, explicit conversion is better.
    # The problem description implies these are numeric values from the model (FloatField).

    # <1> 오른쪽 겹치기 (Existing ends after new starts, Existing starts before new ends)
    if reservations_qs.filter(
        room_type=room_type, room_date=reserve_date,
        room_finish_time__gt=start_time, room_start_time__lt=finish_time
    ).exists():
        return True
    # <2> 사이 들어가기 (Existing starts before or at new start, Existing ends after or at new end)
    # This condition is actually covered by <1> if interpreted broadly or by combining with <3>
    # A more precise "contains" query:
    if reservations_qs.filter(
        room_type=room_type, room_date=reserve_date,
        room_start_time__lte=start_time, room_finish_time__gte=finish_time
    ).exists():
        return True
    # <3> 왼쪽 겹치기 (Existing starts before new ends, Existing ends after new starts)
    # This is symmetric to <1> and essentially the same condition.
    # The original code had "오른쪽 포개지기" which seems like another way to say overlap.
    # if reservations_qs.filter(
    # room_type=room_type,room_date=reserve_date,
    # room_start_time__lt=finish_time, room_finish_time__gt=start_time
    # ).exists():
    # return True # This is identical to <1>

    # <4> 밖에 감싸기 (Existing starts after or at new start, Existing ends before or at new end)
    # This means the new reservation completely envelops an existing one.
    if reservations_qs.filter(
        room_type=room_type, room_date=reserve_date,
        room_start_time__gte=start_time, room_finish_time__lte=finish_time
    ).exists():
        return True

    # The initial set of conditions in the original code seems to cover all overlap scenarios.
    # Let's use a simplified combined condition for overlap:
    # An overlap occurs if (Existing Start < New End) AND (Existing End > New Start)
    if reservations_qs.filter(
        room_type=room_type, room_date=reserve_date,
        room_start_time__lt=finish_time,  # Existing one starts before the new one finishes
        room_finish_time__gt=start_time   # Existing one finishes after the new one starts
    ).exists():
        return True

    return False

# ajax 통신
def check(request):
    room_type_vr = request.POST.get('room_type', None)
    room_date_vr = request.POST.get('room_date', None)
    # Ensure these are floats for comparison if model fields are floats
    try:
        room_start_time_vr = float(request.POST.get('room_start_time', None))
        room_finish_time_vr = float(request.POST.get('room_finish_time', None))
    except (ValueError, TypeError):
        # Handle error: invalid time format
        return HttpResponse(json.dumps({'message': "잘못된 시간 형식입니다.", 'check_error': 1}), content_type="application/json")

    reservations = Reservation.objects.all() # Consider filtering by room_type and date earlier for performance
    reserve_date = datetime.strptime(room_date_vr, "%Y-%m-%d ").date()

    check_error = 0
    message = ""

    # 하루 2건 검사
    if reservations.filter(user=request.user.username, room_date=reserve_date).count() >= 2:
        message = "해당일에 이미 2건의 예약을 하셨습니다"
        check_error = 1
    elif _check_reservation_overlap(reservations, room_type_vr, reserve_date, room_start_time_vr, room_finish_time_vr):
        message = "이미 예약된 시간입니다"
        check_error = 1

    context = {'message': message, 'check_error': check_error}
    return HttpResponse(json.dumps(context), content_type="application/json")

# C
@login_required
def create(request):
    reserve_date = datetime.strptime(request.GET['room_date'], "%Y-%m-%d ").date()

    # 만들기
    reservation = Reservation() # 객체 만들기
    reservation.user = request.GET['user']  # 내용 채우기
    reservation.room_type = request.GET['room_type']  # 내용 채우기
    reservation.room_date= reserve_date # 내용 채우기

    # 시간 구하기
    reservation.room_start_time = request.GET['room_start_time']  # 내용 채우기
    reservation.room_finish_time= request.GET['room_finish_time'] # 내용 채우기
    reservation.pub_date = timezone.datetime.now() # 내용 채우기
    reservation.save() # 객체 저장하기

    # 내 예약 주소
    return redirect('/reservation/my')

# Helper function to get blog posts by category
def get_blog_posts(category_name, count):
    """Fetches the latest 'count' blog posts for a given 'category_name'."""
    return Blog.objects.filter(category=category_name).order_by('-pub_date')[:count]

# Helper function for home view: Calculates room reservation proportions
def _get_room_proportions(today_date):
    room_types = ['1A', '1B', '3A']
    proportion = [0, 0, 0]
    for i, room_type in enumerate(room_types):
        reservations = Reservation.objects.filter(room_date=today_date, room_type=room_type)
        for r in reservations:
            proportion[i] += (r.room_finish_time - r.room_start_time)
    return proportion

########################## R
def home(request):
    today =  datetime.now().date() # Use .date() if only date is relevant for filtering

    proportion = _get_room_proportions(today)
    notices = get_blog_posts(category_name="공지사항", count=3)
    losts = get_blog_posts(category_name="분실물", count=3)

    # Get message from query parameters if present
    msg = request.GET.get('msg', None)

    return render(request, 'reservation/home.html', {'notices':notices, 'losts':losts,  'proportion':proportion, 'msg': msg})

# R 
def detail(request, blog_id) : 
    blog_detail = get_object_or_404(Blog, pk= blog_id) # 특정 객체 가져오기(없으면 404 에러)
    return render(request, 'reservation/detail.html', {'blog':blog_detail})

def index(request, category_name):
    blogs = Blog.objects.filter(category=category_name).order_by('-pub_date')
    category = category_name
    return render(request, 'reservation/index.html', {'category':category, 'blogs':blogs})
########################## U
def edit(request,reservation_id):
    reservation = get_object_or_404(Reservation, pk= reservation_id) # 특정 객체 가져오기(없으면 404 에러)
    min_date = datetime.now().strftime("%Y-%m-%d") # 오늘부터 
    max_date = (datetime.now() +timedelta(days=14)).strftime("%Y-%m-%d") # 14일 후까지 가능
    return render(request, 'reservation/edit.html', {'reservation':reservation, 'min_date':min_date, 'max_date':max_date})

# U
def update(request,reservation_id):
    reservation= get_object_or_404(Reservation, pk= reservation_id) # 특정 객체 가져오기(없으면 404 에러)
    reservation.room_type = request.GET['room_type']  # 내용 채우기
    reservation.room_date= request.GET['room_date'] # 내용 채우기
    reservation.room_start_time = request.GET['room_start_time']  # 내용 채우기
    reservation.room_finish_time= request.GET['room_finish_time'] # 내용 채우기
    reservation.save() # 객체 저장하기

    # 새로운 예약 url 주소로 이동
    return redirect('/reservation/' + str(reservation.id))

########################## D
def delete(request, reservation_id):
    reservation= get_object_or_404(Reservation, pk= reservation_id) # 특정 객체 가져오기(없으면 404 에러)
    if reservation.user == request.user.username:
        reservation.delete()
    return redirect('/reservation/my')                
    
########################## MY 예약
@login_required
def myreservation(request):
    today = date.today() # 오늘날짜
    now_time = datetime.now()
    now = now_time.hour + (now_time.minute / 60) 
    reservations = Reservation.objects.all()
    reservation_list = reservations.filter(Q(user=request.user.username, room_date__gt=today) | Q(user=request.user.username, room_date=today, room_finish_time__gte = now))
    return render(request, 'reservation/myreservation.html',{'reservation_list':reservation_list}) 
    