from flask_restx import Resource, Namespace
from flask import request

from datetime import datetime

from app.models import activity_model
from app.databases import db, cursor

import pymysql
from datetime import date

activity_ns = Namespace('Activity', description='활동 통계 관련 기능', doc='/activity', path='/activity')

activity_field = activity_ns.model('ActivityModel', activity_model)


@activity_ns.route('/')
class ActivityResource(Resource):
    def get(self):
        """
            모든 유저의 활동 조회
        """

        try:
            query = "SELECT email, date, warning_count, activity_count, fall_count FROM activity"
            cursor.execute(query)
            activitys = cursor.fetchall()

            if not activitys:
                return {"message": "No activities found for the given email."}, 404

            activity_list = []

            for activity in activitys:
                activity_dict = {
                    'email': activity[0],
                    'date': activity[1].strftime('%Y-%m-%d'),
                    'warning_count': activity[2],
                    'activity_count': activity[3],
                    'fall_count': activity[4],
                }
                activity_list.append(activity_dict)

            return {'activitys': activity_list}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500

    @activity_ns.expect(activity_field, validate=True)
    def post(self):
        """
            유저의 활동 정보 추가
        """
        if not request.is_json:
            return {"message": "Missing JSON in request."}, 400

        data = request.json

        required_keys = ['email', 'date', 'warning_count', 'activity_count', 'fall_count']
        if not all(key in data for key in required_keys):
            return {"message": "Missing required fields."}, 400

        email = data['email']
        date = data['date']
        warning_count = data['warning_count']
        activity_count = data['activity_count']
        fall_count = data['fall_count']

        try:
            fetch_id_query = "SELECT id FROM users WHERE email = %s"
            cursor.execute(fetch_id_query, (email,))
            user_id_result = cursor.fetchone()
            cursor.fetchall()
            # Check if user exists with the given email
            if not user_id_result:
                return {"message": "User not found with the provided email."}, 404

            query = ("INSERT INTO activity (id, email, date, warning_count, activity_count, fall_count) "
                     "VALUES (%s, %s, %s ,%s, %s, %s)")
            cursor.execute(query, (user_id_result[0], email, date, warning_count, activity_count, fall_count))
            db.commit()

            return {"message": "Activity data added successfully."}, 201

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route('/<string:user_email>')
class ActivityUserResource(Resource):
    def get(self, user_email):
        """
            특정 이메일을 통해 유저 활동 목록 조회
        """
        try:
            query = "SELECT date, warning_count,  activity_count, fall_count FROM activity WHERE email = %s"
            cursor.execute(query, (user_email,))
            activitys = cursor.fetchall()

            if not activitys:
                return {"message": "No activities found for the given email."}, 404

            activity_list = []

            for activity in activitys:
                activity_dict = {
                    'date': activity[0].strftime('%Y-%m-%d'),
                    'warning_count': activity[1],
                    'activity_count': activity[2],
                    'fall_count': activity[3],
                }
                activity_list.append(activity_dict)
            return {'activitys': activity_list}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route('/<string:user_email>/stats/<int:year>/<int:month>')
class ActivityUserStatsResource1(Resource):
    def get(self, user_email, year, month):
        """
            특정 이메일과 년월을 통해 유저 활동 통계 조회
        """
        try:
            query = ("SELECT YEAR(date) AS year, MONTH(date) AS month, email, "
                     "SUM(warning_count) AS warning_count, "
                     "SUM(activity_count) AS activity_count, "
                     "SUM(fall_count) AS fall_count "
                     "FROM activity "
                     "WHERE email = %s and YEAR(date)=%s and MONTH(date)=%s "
                     "GROUP BY YEAR(date), MONTH(date), email")

            cursor.execute(query, (user_email, year, month))
            activitys = cursor.fetchone()
            cursor.fetchall()

            if activitys:
                activity_stats = {
                    'email': activitys[2],
                    'warning_count': int(activitys[3]),
                    'activity_count': int(activitys[4]),
                    'fall_count': int(activitys[5])
                }
                return {'activity_stats': activity_stats}, 200

            else:
                return {'message': 'Activitys not found.'}, 404

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route(
    '/<string:user_email>/stats/<int:start_year>/<int:start_month>/<int:start_day>/<int:end_year>/<int:end_month>/<int:end_day>')
class ActivityUserStatsResource2(Resource):
    def get(self, user_email, start_year, start_month, start_day, end_year, end_month, end_day):
        """
            특정 이메일과 시작 날짜 및 끝 날짜를 통해 유저 활동 통계 조회
        """
        try:
            start_date = date(start_year, start_month, start_day)
            end_date = date(end_year, end_month, end_day)

            query = ("SELECT email, YEAR(date) AS year, MONTH(date) AS month, "
                     "SUM(warning_count) AS warning_count, "
                     "SUM(activity_count) AS activity_count, "
                     "SUM(fall_count) AS fall_count "
                     "FROM activity "
                     "WHERE email = %s AND date BETWEEN %s AND %s "
                     "GROUP BY YEAR(date), MONTH(date), email")

            cursor.execute(query, (user_email, start_date, end_date))
            activitys = cursor.fetchall()

            if not activitys:
                return {"message": "No activities found for the given email."}, 404

            activity_list = []

            if activitys:

                for activity in activitys:
                    activity_stat = {
                        'email': activity[0],
                        'year': activity[1],
                        'month': activity[2],
                        'warning_count': int(activity[3]),
                        'activity_count': int(activity[4]),
                        'fall_count': int(activity[5])
                    }
                    activity_list.append(activity_stat)

                return {'activity_stats': activity_list}, 200

            else:
                return {'message': 'Activitys not found.'}, 404

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route('/check/<string:user_email>')
class ActivityCheckResource(Resource):
    def post(self, user_email):
        """
            오늘 날짜의 데이터(행)가 없으면 새로운 데이터(행) 생성
        """
        try:
            query = "SELECT * FROM activity WHERE email = %s AND date = %s"
            cursor.execute(query, (user_email, datetime.now().date()))
            existing_entry = cursor.fetchone()
            cursor.fetchall()

            if not existing_entry:
                fetch_id_query = "SELECT id FROM users WHERE email = %s"
                cursor.execute(fetch_id_query, (user_email,))
                user_id_result = cursor.fetchone()
                cursor.fetchall()

                # Check if user exists with the given email
                if not user_id_result:
                    return {"message": "User not found with the provided email."}, 404

                else:
                    insert_query = (
                        "INSERT INTO activity (id, email, date, warning_count, activity_count, fall_count)  "
                        "VALUES (%s, %s,%s, %s,%s, %s)")
                    cursor.execute(insert_query, (user_id_result[0], user_email, datetime.now().date(), 0, 0, 0))
                    db.commit()
                    return {"message": "New entry created for the date."}, 201

            else:
                return {'message': 'Data already exists for the date.'}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route('/<string:user_email>/<int:year>/<int:month>/<int:day>')
class ActivityDetailResource1(Resource):
    def get(self, user_email, year, month, day):
        """
            특정 이메일과 년월일을 통해서 활동 조회
        """
        try:
            query = ("SELECT warning_count, activity_count, fall_count FROM activity "
                     "WHERE email = %s AND YEAR(date)=%s AND MONTH(date)=%s AND DAY(date)=%s")
            cursor.execute(query, (user_email, year, month, day))
            activity = cursor.fetchone()
            cursor.fetchall()

            if activity:
                activity_stats = {
                    'warning_count': int(activity[0]),
                    'activity_count': int(activity[1]),
                    'fall_count': int(activity[2])
                }
                return {'activity_stats': activity_stats}, 200
            else:
                return {'message': 'Activitys not found.'}, 404

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500

    @activity_ns.expect(activity_field, validate=True)
    def put(self, user_email, year, month, day):
        """
            특정 이메일과 년월일을 통해서 활동 수정
        """
        try:
            if not request.is_json:
                return {"message": "Missing JSON in request."}, 400

            data = request.json

            if 'email' not in data or 'date' not in data:
                return {"message": "Missing 'email' or 'date' in JSON data."}, 400

            if data['email'] != user_email:
                return {"message": "Mismatch between 'email' in JSON and 'user_email' in path."}, 400

            json_date = datetime.strptime(data['date'], "%Y-%m-%d").date()
            if json_date.year != year or json_date.month != month or json_date.day != day:
                return {"message": "Mismatch between 'date' in JSON and year/month/day in path."}, 400

            required_keys = ['warning_count', 'activity_count', 'fall_count']
            if not all(key in data for key in required_keys):
                return {"message": "Missing required fields."}, 400

            warning_count = data['warning_count']
            activity_count = data['activity_count']
            fall_count = data['fall_count']

            query = ("UPDATE activity SET warning_count = %s, activity_count = %s, fall_count = %s "
                     "WHERE email = %s AND year(date)=%s and month(date)=%s and day(date)=%s;")

            cursor.execute(query, (warning_count, activity_count, fall_count, user_email, year, month, day))
            db.commit()

            updated_rows = cursor.rowcount

            if updated_rows == 0:
                return {'message': 'No data found for the given email and date.'}, 404

            else:
                return {'message': 'Activity data updated successfully.'}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route('/<string:user_email>/<int:year>/<int:month>')
class ActivityDetailResource2(Resource):
    def get(self, user_email, year, month):
        """
            특정 이메일과 년월을 통해서 활동 조회
        """
        try:
            query = ("SELECT date, warning_count, activity_count, fall_count FROM activity "
                     "WHERE email = %s AND YEAR(date)=%s AND MONTH(date)=%s")
            cursor.execute(query, (user_email, year, month))
            activitys = cursor.fetchall()

            if not activitys:
                return {"message": "No activities found for the given email."}, 404

            activity_list = []

            for activity in activitys:
                activity_dict = {
                    'date': activity[0].strftime('%Y-%m-%d'),
                    'warning_count': activity[1],
                    'activity_count': activity[2],
                    'fall_count': activity[3],
                }
                activity_list.append(activity_dict)
            return {'activitys': activity_list}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500


@activity_ns.route('/fall/<string:user_email>/<int:year>/<int:month>/<int:day>')
class ActivityFallDetectionResource(Resource):
    def put(self, user_email, year, month, day):
        """
            Fall 감지시 특정 이메일과 년월일을 통해서 Fall count 수정
        """
        try:
            query = ("SELECT fall_count FROM activity "
                     "WHERE email = %s AND YEAR(date)=%s AND MONTH(date)=%s AND DAY(date)=%s")
            cursor.execute(query, (user_email, year, month, day))
            result = cursor.fetchone()
            cursor.fetchall()

            if not result:
                return {"message": "No activity data found for the given email and date."}, 404

            new_fall_count = result[0] + 1

            update_query = ("UPDATE activity SET fall_count = %s "
                            "WHERE email = %s AND YEAR(date) = %s AND MONTH(date) = %s AND DAY(date) = %s")
            cursor.execute(update_query, (new_fall_count, user_email, year, month, day))
            db.commit()
            return {"message": "Fall count updated successfully."}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500

@activity_ns.route('/activity/<string:user_email>/<int:year>/<int:month>/<int:day>')
class ActivityActivityDetectionResource(Resource):
    def put(self, user_email, year, month, day):
        """
            Activity 감지시 특정 이메일과 년월일을 통해서 Activity count 수정
        """
        try:
            query = ("SELECT activity_count FROM activity "
                     "WHERE email = %s AND YEAR(date)=%s AND MONTH(date)=%s AND DAY(date)=%s")
            cursor.execute(query, (user_email, year, month, day))
            result = cursor.fetchone()
            cursor.fetchall()

            if not result:
                return {"message": "No activity data found for the given email and date."}, 404

            new_activity_count = result[0] + 1

            update_query = ("UPDATE activity SET activity_count = %s "
                            "WHERE email = %s AND YEAR(date) = %s AND MONTH(date) = %s AND DAY(date) = %s")
            cursor.execute(update_query, (new_activity_count, user_email, year, month, day))
            db.commit()
            return {"message": "Activity count updated successfully."}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500

@activity_ns.route('/warning/<string:user_email>/<int:year>/<int:month>/<int:day>')
class ActivityWarningDetectionResource(Resource):
    def put(self, user_email, year, month, day):
        """
            Warning 감지시 특정 이메일과 년월일을 통해서 warning count 수정
        """
        try:
            query = ("SELECT warning_count FROM activity "
                     "WHERE email = %s AND YEAR(date)=%s AND MONTH(date)=%s AND DAY(date)=%s")
            cursor.execute(query, (user_email, year, month, day))
            result = cursor.fetchone()
            cursor.fetchall()

            if not result:
                return {"message": "No activity data found for the given email and date."}, 404

            new_warning_count = result[0] + 1

            update_query = ("UPDATE activity SET warning_count = %s "
                            "WHERE email = %s AND YEAR(date) = %s AND MONTH(date) = %s AND DAY(date) = %s")
            cursor.execute(update_query, (new_warning_count, user_email, year, month, day))
            db.commit()
            return {"message": "Fall count updated successfully."}, 200

        except pymysql.Error as e:
            return {"message": "Database error: {}".format(e)}, 500