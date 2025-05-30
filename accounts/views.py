from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import Profile
from django.utils import timezone
from datetime import datetime, timedelta
from reservation.models import Reservation, Blog
# Import the new helper function
from reservation.views import get_blog_posts
from django.contrib import auth

# PW 찾기 관련
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse_lazy


# SMTP 관련 인증
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_text
# Import reverse for redirecting with URL names
from django.urls import reverse
from .tokens import account_activation_token

# Helper function to send activation email
def send_activation_email(request, user, current_site, uid, token):
    message = render_to_string('accounts/activation_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': uid,
        'token': token,
    })
    mail_title = "사회대 스터디룸 예약 시스템 계정 활성화 확인"
    mail_to = user.email
    email = EmailMessage(mail_title, message, to=[mail_to])
    email.send()

def signup(request):
    # 포스트 방식으로 들어오면
    if request.method == 'POST':
        # 비밀번호 확인도 같다면
        if request.POST['password1'] ==request.POST['password2']:
            # 유저 만들기
            mail_to = request.POST["email"] + "@knu.ac.kr" # 학교 웹메일
            
            # 이메일이 있다면 실패
            if len(User.objects.filter(email=mail_to)) == 0:
                user = User.objects.create_user(username=request.POST['username'], email=mail_to, password=request.POST['password1'])
                user.is_active = False
                user.save()
                realname = request.POST['realname'] # 실명
                department = request.POST['department'] # 소속
                profile = Profile(user=user, realname=realname, department=department)
                profile.save() # 저장

                current_site = get_current_site(request)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = account_activation_token.make_token(user)
                send_activation_email(request, user, current_site, uid, token)

                msg = mail_to + " 주소로 인증 메일을 발송하였습니다. " + "인증 후 이용해주세요."
                # Redirect to reservation home view with a success message
                # Make sure 'home' is the correct name of the URL pattern for reservation.views.home
                return redirect(f"{reverse('home')}?msg={msg}")
            else:
                msg = mail_to + "의 이메일로 인증한 학번 계정이 존재합니다. 비밀번호 재설정을 이용해주세요"
                return render(request, 'accounts/login.html', {'msg':msg})
    # 포스트 방식 아니면 페이지 띄우기
    return render(request, 'accounts/signup.html')


# 메일확인
def confirm(request):
    return render(request, 'accounts/confirm.html')

def login(request):
    # 포스트 방식으로 들어오면
    if request.method == 'POST':
        # 정보 가져와서 
        username = request.POST['username']
        password = request.POST['password']
        # 로그인
        user = auth.authenticate(request, username=username, password=password)
        # 성공
        if user is not None:
            auth.login(request, user)
            return redirect('home')
        # 실패
        else:
            return render(request, 'accounts/login.html', {'msg': '학번 또는 비밀번호가 틀렸거나 웹 메일이 인증되지 않았습니다.'})
    else:
        return render(request, 'accounts/login.html')

def logout(request):
    # 포스트 방식으로 들어오면
    if request.method == 'POST':
        # 유저 로그아웃
        auth.logout(request)
        return redirect('home')
    # GET 요청 시 홈으로 리다이렉트
    return redirect('home')

def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExsit):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        auth.login(request, user)
        return redirect("home")
    else:
        # Use the helper function to get notices and lost items
        notices = get_blog_posts(category_name="공지사항", count=3)
        losts = get_blog_posts(category_name="분실물", count=3)
        # The proportion data is not available here, and might not be necessary for this error page.
        # If it's crucial, activate might need to redirect to home with a message,
        # or home view logic needs to be more flexible.
        # For now, rendering reservation/home.html without proportion.
        # Consider creating a dedicated error display page or using Django messages framework.
        return render(request, 'reservation/home.html', {'notices':notices, 'losts':losts, 'msg' : '웹 메일 인증 오류가 발생하였습니다'})
    # There was a 'return' statement here with no value, which is unnecessary.
    # If the intention was to ensure the function always returns an HttpResponse,
    # the else block already does. If user is None and token check fails, it falls through.
    # However, the original code also had a 'return' at the very end.
    # It should be 'return redirect("home")' or similar if activation fails but user is None.
    # For now, I'll remove the bare 'return' and ensure the else branch is always hit if not successful.
    # The original logic implies if user is None OR token is invalid, it shows the error.
    # The 'return' at the end of the function is unreachable if the if/else covers all paths.
    # Let's assume the current if/else structure is intended and the final 'return' was an artifact.

class MyPasswordResetView(PasswordResetView):
    success_url=reverse_lazy('login')
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset.html'
    mail_title="비밀번호 재설정"
    # html_email_template_name = ...

    def form_valid(self, form):
        return super().form_valid(form)

class MyPasswordResetConfirmView(PasswordResetConfirmView):
    success_url=reverse_lazy('login')
    template_name = 'accounts/password_reset_confirm.html'

    def form_valid(self, form):
        # messages.info(self.request, '암호 리셋을 완료했습니다.')
        return super().form_valid(form)