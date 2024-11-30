import psycopg2
import re
import json
from datetime import datetime

def check_username_in_db(username):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT "USERNAME" FROM "USER" WHERE "USERNAME" = '{username}' """)
    user_name = cursor.fetchone()
    if user_name is not None:
        if user_name[0] == username:
            return 1
    else:
        return 0


def check_username_len(username):
    return 2 <= len(username) <= 25


def check_username_symbols(username):
    # Проверка наличия служебных символов
    forbidden_symbols = {' ', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-',
                         '_', '=', '+', '[', ']', '{', '}', '|', '\\', ';', ':', "'",
                         '"', ',', '.', '<', '>', '/', '?'}
    if any(char in forbidden_symbols for char in username):
        return 0

    # Проверка ASCII-символов с кодами 0-31
    if any(ord(char) < 32 for char in username):
        return 0

    # Проверка наличия символов русского алфавита
    if any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in username):
        return 0

    return 1


def check_password_len(password):
    return 8 <= len(password) <= 25


def check_password_symbols(password):
    if any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in password):
        return 0

    # Проверка ASCII-символов с кодами 0-31
    if any(0 <= ord(char) <= 31 for char in password):
        return 0

    return 1


def check_confirm_password(password, password_confirmation):
    return password == password_confirmation


def check_user_info(username, password, confirm_password):
    return check_username_len(username) and check_username_symbols(username) and not check_username_in_db(username) \
        and check_password_len(password) and check_password_symbols(password) \
        and check_confirm_password(password, confirm_password)


def check_email_exists(email):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432", database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT COUNT(*) FROM "MEMBER" WHERE "MEMBER_EMAIL" = '{email}'""")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0


def check_trainer_email_exists(email):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432", database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT COUNT(*) FROM "TRAINER" WHERE "TRAINER_EMAIL" = '{email}'""")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0


def check_trainer_phone_exists(phone):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                            database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT COUNT(*) FROM "TRAINER" WHERE "TRAINER_PHONE" = '{phone}'""")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0


def check_phone_exists(phone):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432", database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT COUNT(*) FROM "MEMBER" WHERE "MEMBER_PHONE" = %s""", (phone,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0


def check_password_exists(password):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432", database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT COUNT(*) FROM "USER" WHERE "PASSWORD" = '{password}'""")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0


def has_profile_data(user_id):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                            database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT * FROM "MEMBER" WHERE "USER_ID" = '{user_id}'""")
    profile_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return profile_data is not None

# Функция для выполнения SQL-запросов и получения результата из базы данных
def execute_query(query, params=None):
    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone()[0]  # Получение единственного значения
    cursor.close()
    connection.close()
    return result

# Функция для получения количества зарегистрированных участников на тренировке с учетом даты
def get_registered_count_for_workout(workout_id, visit_date):

    registered_count = execute_query(f"""SELECT COUNT(*) AS "REGISTERED_COUNT" FROM "MEMBER_WORKOUT" 
                WHERE "WORKOUT_ID" = '{workout_id}' AND "VISIT_DATE" = '{visit_date}'""")
    return registered_count

# Функция для получения максимального количества участников для тренировки
def get_max_participants_for_workout(workout_id):
    query = f"""SELECT "MAX_PARTICIPANTS" FROM "WORKOUT" WHERE "WORKOUT_ID" = '{workout_id}'"""
    max_participants = execute_query(query)
    return max_participants


def check_duplicate_workout_registration(user_id, workout_id, visit_date):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                            database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT COUNT(*) FROM "MEMBER_WORKOUT" 
                        WHERE "USER_ID" = '{user_id}' AND "WORKOUT_ID" = '{workout_id}' 
                        AND "VISIT_DATE" = '{visit_date}'""")

    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count > 0


def delete_expired_workouts():
    try:
        connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                      database="FitnessClubDB")
        cursor = connection.cursor()

        current_date = datetime.now().date()

        # Получение и удаление устаревших записей из таблицы MEMBER_MEMBERSHIP
        cursor.execute("""SELECT * FROM "MEMBER_WORKOUT" """)
        workouts = cursor.fetchall()

        for workout in workouts:
            visit_date = workout[1]
            print("Текущая дата:", current_date)
            print("Дата тренировки:", visit_date)
            if current_date > visit_date:
                print("Удаление устаревшей тренировки...")
                cursor.execute(f"""DELETE FROM "MEMBER_WORKOUT" WHERE "USER_ID" = '{workout[2]}' 
                                AND "WORKOUT_ID" = '{workout[0]}'""")

                cursor.execute(f"""UPDATE "WORKOUT" SET "REGISTERED_COUNT" = "REGISTERED_COUNT" - 1 
                                WHERE "WORKOUT_ID" = '{workout[0]}'""")

        connection.commit()
        cursor.close()
        connection.close()

    except (Exception, psycopg2.Error) as error:
        print("Ошибка при удалении устаревших тренировок:", error)



def delete_expired_memberships():
    try:
        connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                      database="FitnessClubDB")
        cursor = connection.cursor()

        current_date = datetime.now().date()

        # Получение и удаление устаревших записей из таблицы MEMBER_MEMBERSHIP
        cursor.execute("""SELECT * FROM "MEMBER_MEMBERSHIP" """)
        memberships = cursor.fetchall()

        for membership in memberships:
            end_date = membership[3]
            if current_date > end_date:
                cursor.execute(f"""DELETE FROM "MEMBER_MEMBERSHIP" WHERE "USER_ID" = '{membership[0]}' 
                                AND "MEMBERSHIP_ID" = '{membership[1]}'""")

        connection.commit()
        cursor.close()
        connection.close()

    except (Exception, psycopg2.Error) as error:
        print("Ошибка при удалении устаревших абонементов:", error)


def check_existing_membership(user_id, membership_id):
    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()
    cursor.execute(f"""SELECT * FROM "MEMBER_MEMBERSHIP" WHERE "USER_ID" = '{user_id}' 
    AND "MEMBERSHIP_ID" = '{membership_id}' """)

    existing_membership = cursor.fetchone()
    cursor.close()
    connection.close()

    return existing_membership


def generate_data_for_admin_user_list(username):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                            database="FitnessClubDB")

    cursor = conn.cursor()

    if username.isdigit():
        cursor.execute(f"""SELECT U."USER_ID", U."USERNAME", M."MEMBER_NAME", M."MEMBER_EMAIL",M."MEMBER_PHONE",
         M."MEMBER_GENDER", M."MEMBER_DOB", M."MEMBER_JOINED_DATE"  FROM "USER" AS U JOIN "MEMBER" AS M 
         ON U."USER_ID" = M."USER_ID" WHERE U."USER_ID" = {username}; """)

        user_info_list = cursor.fetchone()

        if user_info_list is not None:

            result_string = f"""
                <p>
                <b>ID:</b> {user_info_list[0]}<br>
                <b>Логин:</b> {user_info_list[1]}<br>
                <b>Имя:</b> {user_info_list[2]}<br>
                <b>Почта:</b> {user_info_list[3]}<br>
                <b>Телефон:</b> {user_info_list[4]}<br>
                <b>Пол:</b> {user_info_list[5]}<br>
                <b>Дата рождения:</b> {user_info_list[6]}<br>
                <b>Дата регистрации:</b> {user_info_list[7]}<br>
                </p>
            """

            cursor.close()
            conn.close()

            return result_string
        else:
            cursor.close()
            conn.close()

            return "<p>Пользователи отсутствуют</p>"

    if username in ['Все', 'Всё', 'все', 'всё']:
        cursor.execute(f"""SELECT U."USER_ID", U."USERNAME", M."MEMBER_NAME", M."MEMBER_EMAIL",M."MEMBER_PHONE",
         M."MEMBER_GENDER", M."MEMBER_DOB", M."MEMBER_JOINED_DATE"  FROM "USER" AS U JOIN "MEMBER" AS M 
         ON U."USER_ID" = M."USER_ID" WHERE U."ROLE" = 'MEMBER'; """)

        user_info_list = cursor.fetchall()

        result_strings = ''

        for user_info in user_info_list:

            result_string = f"""
                <p>
                <b>ID:</b> {user_info[0]}<br>
                <b>Логин:</b> {user_info[1]}<br>
                <b>Имя:</b> {user_info[2]}<br>
                <b>Почта:</b> {user_info[3]}<br>
                <b>Телефон:</b> {user_info[4]}<br>
                <b>Пол:</b> {user_info[5]}<br>
                <b>Дата рождения:</b> {user_info[6]}<br>
                <b>Дата регистрации:</b> {user_info[7]}<br>
                </p>
            """

            result_strings += result_string

        cursor.close()
        conn.close()

        return result_strings

    if check_username_in_db(username):
        cursor.execute(f"""SELECT U."USER_ID", U."USERNAME", M."MEMBER_NAME", M."MEMBER_EMAIL",M."MEMBER_PHONE",
         M."MEMBER_GENDER", M."MEMBER_DOB", M."MEMBER_JOINED_DATE"  FROM "USER" AS U JOIN "MEMBER" AS M 
         ON U."USER_ID" = M."USER_ID" WHERE U."USERNAME" = '{username}'; """)
        user_info_list = cursor.fetchone()

        if user_info_list is not None:

            result_string = f"""
                <p>
                <b>ID:</b> {user_info_list[0]}<br>
                <b>Логин:</b> {user_info_list[1]}<br>
                <b>Имя:</b> {user_info_list[2]}<br>
                <b>Почта:</b> {user_info_list[3]}<br>
                <b>Телефон:</b> {user_info_list[4]}<br>
                <b>Пол:</b> {user_info_list[5]}<br>
                <b>Дата рождения:</b> {user_info_list[6]}<br>
                <b>Дата регистрации:</b> {user_info_list[7]}<br>
                </p>
            """

            cursor.close()
            conn.close()

            return result_string
        else:
            cursor.close()
            conn.close()

            return "<p>Что-то не так...</p>"

    else:
        cursor.close()
        conn.close()

        return "<p>Что-то не так...</p>"



def check_trainer_in_db(trainer_name):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT * FROM "TRAINER" WHERE "TRAINER_NAME" LIKE '%{trainer_name.title()}%';""")
    train_name = cursor.fetchone()
    if train_name is not None:
        return 1
    else:
        return 0

def check_trainerId_in_db(trainer_id):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()

    if trainer_id.isdigit():
        cursor.execute(f"""SELECT COUNT(*) FROM "TRAINER" WHERE "TRAINER_ID" = '{trainer_id}';""")
        trainer = cursor.fetchone()

        if trainer is not None:
            count = trainer[0]
            return count
    else:
        return 0

def generate_data_for_admin_trainer_list(trainer_name):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()
    if trainer_name.isdigit():
        cursor.execute(f"""SELECT * FROM "TRAINER" WHERE "TRAINER_ID" = {trainer_name}; """)

        trainer_info_list = cursor.fetchone()

        if trainer_info_list is not None:

            result_string = f"""
                <p>
                <b>ID:</b> {trainer_info_list[0]}<br>   
                <b>Имя:</b> {trainer_info_list[1]}<br>
                <b>Почта:</b> {trainer_info_list[2]}<br>
                <b>Телефон:</b> {trainer_info_list[3]}<br>
                <b>Специализация:</b> {trainer_info_list[4]}<br>
                </p>
            """

            cursor.close()
            conn.close()

            return result_string
        else:
            cursor.close()
            conn.close()

            return "<p>Тренеры отсутствуют</p>"

    if trainer_name in ['Все', 'Всё', 'все', 'всё']:
        cursor.execute(f"""SELECT * FROM "TRAINER" ORDER BY "TRAINER_ID"; """)

        trainer_info_list = cursor.fetchall()

        result_strings = ''

        for trainer_info in trainer_info_list:

            result_string = f"""
                <p>
                <b>ID:</b> {trainer_info[0]}<br>
                <b>Имя:</b> {trainer_info[1]}<br>
                <b>Почта:</b> {trainer_info[2]}<br>
                <b>Телефон:</b> {trainer_info[3]}<br>
                <b>Специализация:</b> {trainer_info[4]}<br>
                </p>
            """

            result_strings += result_string

        cursor.close()
        conn.close()

        return result_strings

    if check_trainer_in_db(trainer_name):

        cursor.execute(f"""SELECT * FROM "TRAINER" WHERE "TRAINER_NAME" LIKE '%{trainer_name.title()}%';""")

        trainer_info_list = cursor.fetchone()

        if trainer_info_list is not None:

            result_string = f"""
                <p>
                <b>ID:</b> {trainer_info_list[0]}<br>
                <b>Имя:</b> {trainer_info_list[1]}<br>
                <b>Почта:</b> {trainer_info_list[2]}<br>
                <b>Телефон:</b> {trainer_info_list[3]}<br>
                <b>Специализация:</b> {trainer_info_list[4]}<br>
                </p>
            """

            cursor.close()
            conn.close()

            return result_string
        else:
            cursor.close()
            conn.close()

            return "<p>Что-то не так...</p>"

    else:
        cursor.close()
        conn.close()

        return "<p>Что-то не так...</p>"

def get_trainer_data_for_edit(trainer_id):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()

    cursor.execute(f"""SELECT "TRAINER_NAME", "TRAINER_EMAIL", "TRAINER_PHONE", "TRAINER_SPECIALIZATION", "IMAGE_URL"
     FROM "TRAINER" WHERE "TRAINER_ID" = '{trainer_id}'""")
    trainer_info = cursor.fetchone()

    cursor.close()
    conn.close()

    trainer_data = {
        'name': trainer_info[0],
        'email': trainer_info[1],
        'phone': trainer_info[2],
        'specialization': trainer_info[3],
        'img': trainer_info[4]
    }
    return trainer_data



def check_workout_in_db(workout_name):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()
    cursor.execute(f"""SELECT * FROM "WORKOUT" WHERE LOWER(TRIM("NAME")) LIKE '%{workout_name.lower()}%';""")
    work_name = cursor.fetchone()
    if work_name is not None:
        return 1
    else:
        return 0

def check_workoutId_in_db(workout_id):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()

    if workout_id.isdigit():
        cursor.execute(f"""SELECT COUNT(*) FROM "WORKOUT" WHERE "WORKOUT_ID" = '{workout_id}';""")
        workout = cursor.fetchone()

        if workout is not None:
            count = workout[0]
            return count
    else:
        return 0

def get_workout_data_for_edit(workout_id):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()

    cursor.execute(f"""SELECT "NAME", "DESCRIPTION", "MAX_PARTICIPANTS", "COST", "WORKOUT_SCHEDULE"
    FROM "WORKOUT" WHERE "WORKOUT_ID" = '{workout_id}'""")
    workout_info = cursor.fetchone()

    cursor.close()
    conn.close()

    formatted_schedule = '\n'.join([f'{key}: {value}' for key, value in workout_info[4].items()])

    workout_data = {
        'name': workout_info[0],
        'description': workout_info[1],
        'max_participants': workout_info[2],
        'cost': workout_info[3],
        'schedule': formatted_schedule
    }

    return workout_data

def generate_data_for_admin_workout_list(workout_name):
    conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = conn.cursor()
    if workout_name.isdigit():
        cursor.execute(f"""SELECT * FROM "WORKOUT" WHERE "WORKOUT_ID" = {workout_name}; """)

        workout_info_list = cursor.fetchone()
        print(workout_info_list)
        if workout_info_list is not None:

            result_string = f"""
                <p>
                <b>ID:</b> {workout_info_list[0]}<br>   
                <b>Название:</b> {workout_info_list[2]}<br>
                <b>Описание:</b> {workout_info_list[3]}<br>
                <b>Макс. участников:</b> {workout_info_list[4]}<br>
                <b>Цена:</b> {workout_info_list[5]} BYN<br>
                <b>Расписание:</b> {workout_info_list[6]}<br>
                </p>
            """

            cursor.close()
            conn.close()

            return result_string
        else:
            cursor.close()
            conn.close()

            return "<p>Тренировки отсутствуют</p>"

    if workout_name in ['Все', 'Всё', 'все', 'всё']:
        cursor.execute(f"""SELECT * FROM "WORKOUT" ORDER BY "WORKOUT_ID"; """)

        workout_info_list = cursor.fetchall()

        result_strings = ''

        for workout_info in workout_info_list:

            result_string = f"""
                <p>
                <b>ID:</b> {workout_info[0]}<br>   
                <b>Название:</b> {workout_info[2]}<br>
                <b>Описание:</b> {workout_info[3]}<br>
                <b>Макс. участников:</b> {workout_info[4]}<br>
                <b>Цена:</b> {workout_info[5]} BYN<br>
                <b>Расписание:</b> {workout_info[6]}<br>
                </p>
            """

            result_strings += result_string

        cursor.close()
        conn.close()

        return result_strings

    if check_workout_in_db(workout_name):

        cursor.execute(f"""SELECT * FROM "WORKOUT" WHERE LOWER(TRIM("NAME")) LIKE '%{workout_name.lower()}%' 
        ORDER BY "WORKOUT_ID"; """)

        workout_info_list = cursor.fetchall()

        result_strings = ''

        for workout_info in workout_info_list:
            result_string = f"""
                <p>
                <b>ID:</b> {workout_info[0]}<br>   
                <b>Название:</b> {workout_info[2]}<br>
                <b>Описание:</b> {workout_info[3]}<br>
                <b>Макс. участников:</b> {workout_info[4]}<br>
                <b>Цена:</b> {workout_info[5]} BYN<br>
                <b>Расписание:</b> {workout_info[6]}<br>
                </p>
            """

            result_strings += result_string

        cursor.close()
        conn.close()

        return result_strings


    else:
        cursor.close()
        conn.close()

        return "<p>Что-то не так...</p>"


def validate_day_time(day, time):
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    day_pattern = re.compile(r'\b(?:' + '|'.join(days_of_week) + r')\b', re.IGNORECASE)
    time_pattern = re.compile(r'^\d{1,2}:\d{2}$')

    return bool(day_pattern.match(day)) and bool(time_pattern.match(time))




