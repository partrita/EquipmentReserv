from django.test import TestCase
from django.contrib.auth.models import User # For creating test users if needed by helpers
from unittest.mock import patch, MagicMock, call
from datetime import datetime, date, timedelta

# Functions to test from reservation.views
from .views import (
    _get_week_start_day_and_params,
    _get_daily_reservations_list,
    _check_reservation_overlap,
    _get_room_proportions,
    get_blog_posts,
)
# Models that might be needed for mocking
from .models import Reservation, Blog
# myrange function (it's used by _get_daily_reservations_list)
from utils import myrange # Assuming myrange is in the root utils.py

class GetWeekStartDayAndParamsTests(TestCase):
    def test_weekday_input(self):
        # Monday, January 6, 2020
        today = datetime(2020, 1, 6)
        start_day, start_day_diff, weekday_mark, date_diff = _get_week_start_day_and_params(today)
        self.assertEqual(start_day, datetime(2020, 1, 6)) # Should be Monday
        self.assertEqual(start_day_diff, 0)
        self.assertEqual(weekday_mark, 0)
        self.assertEqual(date_diff, 4) # 4 - 0 (Monday)

    def test_weekend_input_saturday(self):
        # Saturday, January 11, 2020
        today = datetime(2020, 1, 11)
        start_day, start_day_diff, weekday_mark, date_diff = _get_week_start_day_and_params(today)
        self.assertEqual(start_day, datetime(2020, 1, 13))
        self.assertEqual(start_day_diff, 2)
        self.assertEqual(weekday_mark, 2)
        self.assertEqual(date_diff, 6)

    def test_weekend_input_sunday(self):
        # Sunday, January 12, 2020
        today = datetime(2020, 1, 12)
        start_day, start_day_diff, weekday_mark, date_diff = _get_week_start_day_and_params(today)
        self.assertEqual(start_day, datetime(2020, 1, 13))
        self.assertEqual(start_day_diff, 1)
        self.assertEqual(weekday_mark, 1)
        self.assertEqual(date_diff, 5)


class GetDailyReservationsListTests(TestCase):
    @patch('reservation.views.Reservation.objects')  # Patch the model manager
    def test_get_daily_reservations_list_structure(self, mock_reservation_manager):
        expected_slots_day0 = list(myrange(9.0, 10.0, 0.5)) + list(myrange(14.0, 15.0, 0.5))
        expected_slots_day2 = list(myrange(11.0, 11.5, 0.5))

        mock_res_day0_event1 = MagicMock(spec=Reservation, room_start_time=9.0, room_finish_time=10.0)
        mock_res_day0_event2 = MagicMock(spec=Reservation, room_start_time=14.0, room_finish_time=15.0)
        iterable_reservations_day0 = [mock_res_day0_event1, mock_res_day0_event2]

        mock_res_day2_event1 = MagicMock(spec=Reservation, room_start_time=11.0, room_finish_time=11.5)
        iterable_reservations_day2 = [mock_res_day2_event1]

        def filter_side_effect(**kwargs):
            queryset_mock = MagicMock()
            # 'room_date' in kwargs will be a datetime object from the helper function
            filter_datetime_obj = kwargs.get('room_date')
            # Convert to date for comparison, as model field is DateField and ORM might pass date part
            filter_date_obj = filter_datetime_obj.date()

            if filter_date_obj == date(2020, 1, 6):
                queryset_mock.order_by.return_value = iterable_reservations_day0
            elif filter_date_obj == date(2020, 1, 8):
                queryset_mock.order_by.return_value = iterable_reservations_day2
            else:
                queryset_mock.order_by.return_value = []
            return queryset_mock

        mock_reservation_manager.filter.side_effect = filter_side_effect

        start_day_datetime = datetime(2020, 1, 6)
        room_type = '1A'
        username = 'testuser'

        day_list = _get_daily_reservations_list(mock_reservation_manager, room_type, username, start_day_datetime, myrange)

        self.assertEqual(len(day_list), 5)
        self.assertEqual(day_list[0], expected_slots_day0)
        self.assertEqual(day_list[1], [])
        self.assertEqual(day_list[2], expected_slots_day2)
        self.assertEqual(day_list[3], [])
        self.assertEqual(day_list[4], [])

        expected_filter_calls = [
            call(room_type=room_type, user=username, room_date=datetime(2020, 1, 6, 0, 0)),
            call(room_type=room_type, user=username, room_date=datetime(2020, 1, 7, 0, 0)),
            call(room_type=room_type, user=username, room_date=datetime(2020, 1, 8, 0, 0)),
            call(room_type=room_type, user=username, room_date=datetime(2020, 1, 9, 0, 0)),
            call(room_type=room_type, user=username, room_date=datetime(2020, 1, 10, 0, 0)),
        ]
        self.assertEqual(mock_reservation_manager.filter.call_args_list, expected_filter_calls)

        # Check that order_by was called for each mock returned by filter
        # This relies on filter_side_effect returning distinct mocks that we can check.
        # Iterate through the calls made to the filter mock
        for call_made in mock_reservation_manager.filter.mock_calls:
            # Get the mock object that was returned by this specific filter call
            # This is call_made.return_value
            filter_return_mock = call_made.return_value
            filter_return_mock.order_by.assert_called_with('room_start_time')


class CheckReservationOverlapTests(TestCase):
    @patch('reservation.views.Reservation.objects')
    def test_overlap_conditions(self, mock_reservation_objects):
        mock_qs = mock_reservation_objects.filter.return_value

        room_type = '1A'
        reserve_date = date(2020, 1, 6)

        mock_qs.exists.return_value = False
        self.assertFalse(_check_reservation_overlap(mock_reservation_objects, room_type, reserve_date, 9.0, 10.0))

        mock_qs.exists.return_value = True
        self.assertTrue(_check_reservation_overlap(mock_reservation_objects, room_type, reserve_date, 9.0, 10.0))

class GetRoomProportionsTests(TestCase):
    @patch('reservation.views.Reservation.objects.filter')
    def test_get_room_proportions_calculation(self, mock_filter):
        today = date(2020, 1, 6)

        mock_reservations_1A = [
            MagicMock(room_start_time=9.0, room_finish_time=10.0),
            MagicMock(room_start_time=11.0, room_finish_time=11.5)
        ]
        mock_reservations_1B = [ MagicMock(room_start_time=14.0, room_finish_time=16.0) ]
        mock_reservations_3A = []

        def filter_side_effect(room_date, room_type):
            if room_date == today and room_type == '1A': return mock_reservations_1A
            if room_date == today and room_type == '1B': return mock_reservations_1B
            if room_date == today and room_type == '3A': return mock_reservations_3A
            return []

        mock_filter.side_effect = filter_side_effect
        proportions = _get_room_proportions(today)
        self.assertEqual(proportions, [1.5, 2.0, 0.0])
        mock_filter.assert_has_calls([
            call(room_date=today, room_type='1A'),
            call(room_date=today, room_type='1B'),
            call(room_date=today, room_type='3A'),
        ], any_order=False) # any_order=False is default but good to be explicit


class GetBlogPostsTests(TestCase):
    @patch('reservation.views.Blog.objects')
    def test_get_blog_posts_fetches_correctly(self, mock_blog_objects):
        mock_final_posts = [MagicMock(spec=Blog), MagicMock(spec=Blog)]
        mock_ordered_qs = MagicMock()
        mock_blog_objects.filter.return_value.order_by.return_value = mock_ordered_qs
        mock_ordered_qs.__getitem__.return_value = mock_final_posts

        category_name = "공지사항"
        count = 3
        result = get_blog_posts(category_name, count)

        mock_blog_objects.filter.assert_called_once_with(category=category_name)
        mock_blog_objects.filter.return_value.order_by.assert_called_once_with('-pub_date')
        mock_ordered_qs.__getitem__.assert_called_once_with(slice(None, count, None))
        self.assertEqual(result, mock_final_posts)

# Example run commands:
# python manage.py test accounts.tests.SendActivationEmailTests
# python manage.py test reservation.tests.GetDailyReservationsListTests
# python manage.py test reservation
# python manage.py test
