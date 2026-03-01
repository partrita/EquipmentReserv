from django.db import models
from django.utils import timezone
from ckeditor_uploader.fields import RichTextUploadingField

class Equipment(models.Model):
    name = models.CharField(max_length=50, verbose_name="장비 이름")
    description = models.TextField(blank=True, verbose_name="장비 설명")
    
    def __str__(self):
        return self.name

class Reservation(models.Model):
    user = models.CharField(max_length=10, verbose_name="예약자 학번/이름")
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, verbose_name="예약 장비", null=True)
    room_date = models.DateField(max_length=20, verbose_name="예약 날짜")
    room_start_time = models.FloatField(verbose_name="시작 시간 (0-24)")
    room_finish_time = models.FloatField(verbose_name="종료 시간 (0-24)")
    pub_date = models.DateTimeField(default=timezone.now, verbose_name="작성 일시")

    def __str__(self):
        return f"{self.user} - {self.equipment.name if self.equipment else 'N/A'} ({self.room_date})"

class Blog(models.Model):
    category = models.CharField(max_length=20, default='공지사항')
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    description = RichTextUploadingField(blank=True, null=True)

    def __str__(self):
        return self.title