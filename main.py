from flask import Flask, render_template, request, redirect, url_for, session, jsonify, make_response
from psycopg2 import Binary
from datetime import date, time, datetime
from dateutil.relativedelta import relativedelta
import psycopg2
from psycopg2 import errors
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename
import json
from decimal import Decimal
import db_functions
from PIL import Image

app = Flask(__name__)
app.secret_key = '8888888888'
bcrypt = Bcrypt(app)

app.config['UPLOAD_FOLDER'] = 'static/trainer_images'  # Указываем папку для хранения изображений тренеров

# Функция для выполнения SQL-запросов и коммита транзакций
def execute_query(query, params=None):
    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()
    cursor.execute(query, params)
    connection.commit()
    cursor.close()
    connection.close()

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/registration")
def registration():
    return render_template('registration.html')

@app.route("/log_in")
def log_in():
    return render_template('log_in.html')

@app.route("/member_info")
def member_info():
    return render_template('member_info.html')

@app.route("/recovery_password")
def recovery_password():
    return render_template('password_recovery.html')

@app.route("/admin")
def admin():
    return render_template('admin_panel.html')


@app.route("/register", methods=['POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirmation = request.form['password_confirmation']
        if db_functions.check_user_info(username, password, password_confirmation):
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            execute_query(f"""INSERT INTO "USER" ("USERNAME", "PASSWORD") VALUES ('{username}',
            '{hashed_password}') """)

            # Получаем user_id, который только что был создан
            conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                    database="FitnessClubDB")
            cursor = conn.cursor()
            cursor.execute(f"""SELECT "USER_ID" FROM "USER" WHERE "USERNAME" = '{username}'""")
            user_id = cursor.fetchone()[0]

            # Сохраняем user_id в сессии
            session['user_id'] = int(user_id)

            return redirect(url_for('member_info'))

        else:
            errors = []

            if not db_functions.check_username_len(username):
                errors.append('Некорректный логин')
                errors.append('(длина от 2 до 25 символов)')
            elif not db_functions.check_username_symbols(username):
                errors.append('Логин содержит')
                errors.append('недопустимые символы')
            elif db_functions.check_username_in_db(username):
                errors.append('Логин уже используется')
            elif not db_functions.check_password_len(password):
                errors.append('Некорректный пароль')
                errors.append('(длина от 8 до 25 символов)')
            elif not db_functions.check_password_symbols(password):
                errors.append('Пароль содержит')
                errors.append('недопустимые символы')
            elif not db_functions.check_confirm_password(password, password_confirmation):
                errors.append('Пароли не совпадают')

    return render_template('registration.html', username=username, password=password,
                           password_confirmation=password_confirmation, errors=errors)


@app.route("/vhod", methods=['POST', 'GET'])
def vhod():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                database="FitnessClubDB")
        cursor = conn.cursor()
        cursor.execute(f"""SELECT "USER_ID","USERNAME","PASSWORD", "ROLE" FROM "USER" WHERE 
        "USERNAME" = '{username}'""")
        user_info = cursor.fetchone()

        if user_info and bcrypt.check_password_hash(user_info[2], password):
            cursor.close()
            conn.close()
            session['user_id'] = user_info[0]
            session['password'] = password

            # Проверка роли пользователя
            if user_info[3].lower() == 'admin':
                return redirect(url_for('admin'))  # Перенаправление на панель админа

            # Проверка наличия персональных данных в таблице MEMBER
            if not db_functions.has_profile_data(user_info[0]):
                return redirect(url_for('member_info'))

            return redirect(url_for('prof'))

        errors = []

        if not db_functions.check_username_len(username):
            errors.append('Неверный логин')
        elif not db_functions.check_username_in_db(username):
            errors.append('Пользователя с таким')
            errors.append('логином не существует')

        elif not db_functions.check_password_len(password) or not db_functions.check_password_exists(password) or password is None:
            errors.append('Неверный пароль')

    else:
        return 'error'

    return render_template('log_in.html', username=username, password=password, errors=errors)


@app.route("/memb_inf", methods=['POST'])
def memb_inf():
    if request.method == 'POST':
        # Получаем user_id из сессии
        user_id = session.get('user_id')

        # Получаем данные из формы HTML
        if user_id:
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            gender = request.form['gender']
            birthdate = request.form['birthdate']

        if not db_functions.check_email_exists(email) and not db_functions.check_phone_exists(phone):
            # Вставляем данные в таблицу MEMBER
            execute_query(f"""INSERT INTO "MEMBER" ("USER_ID", "MEMBER_NAME", "MEMBER_EMAIL", "MEMBER_PHONE",
            "MEMBER_GENDER", "MEMBER_DOB", "MEMBER_JOINED_DATE") VALUES ('{user_id}', '{name}', '{email}',
            '{phone}','{gender}', '{birthdate}', CURRENT_DATE);""")

            return redirect(url_for('prof'))

        else:
            errors = []

            if db_functions.check_email_exists(email):
                errors.append('Почта уже используется')
            # Проверка длины номера телефона
            elif len(phone) != 13:
                errors.append('Неверная длина')
                errors.append('номера телефона')

            elif db_functions.check_phone_exists(phone):
                errors.append('Номер телефона уже используется')

    return render_template('member_info.html', name=name, email=email, phone=phone, gender=gender, birthdate=birthdate, errors=errors)


@app.route("/prof")
def prof():
    user_id = session.get('user_id')

    if user_id:

        connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                      database="FitnessClubDB")
        cursor = connection.cursor()

        # Запрос для получения информации о пользователе
        cursor.execute(f"""SELECT "MEMBER_NAME", "MEMBER_EMAIL", "MEMBER_PHONE", "MEMBER_GENDER", "MEMBER_DOB",
        "MEMBER_JOINED_DATE" FROM "MEMBER" WHERE "USER_ID" = {user_id}""")
        user_info = cursor.fetchone()

        cursor.execute(f"""SELECT W."NAME", T."TRAINER_NAME", M_W."VISIT_DATE", M_W."USER_ID", W."WORKOUT_ID",
        M_W."VISIT_TIME" FROM "MEMBER_WORKOUT" AS M_W JOIN "WORKOUT" AS W ON M_W."WORKOUT_ID" = W."WORKOUT_ID"
        JOIN "TRAINER" AS T ON W."TRAINER_ID" = T."TRAINER_ID" WHERE M_W."USER_ID" = {user_id}""")

        workout_records = cursor.fetchall()

        # Форматирование времени без секунд
        formatted_workout_records = []

        for record in workout_records:
            record_list = list(record)
            record_list[5] = record_list[5].strftime('%H:%M')
            formatted_workout_records.append(record_list)

        cursor.close()
        connection.close()

        db_functions.delete_expired_workouts()

        if user_info:
            name, email, phone, gender, birthdate, joined_date = user_info

            return render_template('profile.html', name=name, email=email, phone=phone, gender=gender,
                                   birthdate=birthdate, joined_date=joined_date,
                                   formatted_workout_records=formatted_workout_records)


@app.route("/train")
def train():

    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()

    # Запрос для получения информации о тренере
    cursor.execute(f"""SELECT * FROM "TRAINER" ORDER BY "TRAINER_ID" """)
    trainers_info = cursor.fetchall()

    cursor.close()
    connection.close()

    if trainers_info:

        return render_template('trainers.html', trainers_info=trainers_info)


@app.route("/get_trainer_info/<int:trainer_id>")
def get_trainer_info(trainer_id):

    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()

    # Запрос для получения информации о тренере
    cursor.execute(f"""SELECT * FROM "TRAINER" WHERE "TRAINER_ID" = {trainer_id}""")
    trainer_info = cursor.fetchone()

    cursor.close()
    connection.close()

    if trainer_info:
        # Возвращаем информацию в формате JSON
        return jsonify({
            "name": trainer_info[1],
            "email": trainer_info[2],
            "phone": trainer_info[3],
            "specialization": trainer_info[4]
        })

    return jsonify({"error": "Trainer not found"})


@app.route("/get_workout_info/<int:trainer_id>")
def get_workout_info(trainer_id):

    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()

    # Запрос для получения информации о тренировках
    cursor.execute(f"""SELECT * FROM "WORKOUT" WHERE "TRAINER_ID" = {trainer_id}""")
    workouts = cursor.fetchall()

    workout_list = []

    for workout in workouts:
        workout_data = {
            "WORKOUT_ID": workout[0],
            "TRAINER_ID": workout[1],
            "NAME": workout[2],
            "DESCRIPTION": workout[3],
            "MAX_PARTICIPANTS": workout[4],
            "COST": workout[5],
            "WORKOUT_SCHEDULE": workout[6]
        }
        workout_list.append(workout_data)

    connection.close()
    return jsonify(workout_list)


@app.route('/member_workout', methods=['POST'])
def member_workout():
    data = request.get_json()

    user_id = data['user_id']
    workout_id = data['workout_id']
    visit_date = data['visit_date']
    visit_time = data['visit_time']

    if db_functions.check_duplicate_workout_registration(user_id, workout_id, visit_date):
        return 'Вы уже записаны на эту тренировку в этот день'

    # Получение информации о количестве зарегистрированных пользователей на тренировке с учетом даты
    registered_count = db_functions.get_registered_count_for_workout(workout_id, visit_date)

    # Получение максимального количества участников для тренировки
    max_participants = db_functions.get_max_participants_for_workout(workout_id)

    # Проверка доступности мест
    if registered_count < max_participants:
        # Выполнение запроса на добавление записи о новом участнике
        execute_query(f"""INSERT INTO "MEMBER_WORKOUT" ("USER_ID", "WORKOUT_ID", "VISIT_DATE", "VISIT_TIME") 
        VALUES ('{user_id}', '{workout_id}', '{visit_date}', '{visit_time}')""")

        # Обновление количества зарегистрированных участников для тренировки
        execute_query(f"""UPDATE "WORKOUT" SET "REGISTERED_COUNT" = "REGISTERED_COUNT" + 1 
        WHERE "WORKOUT_ID" = '{workout_id}'""")

        return 'Запись успешно добавлена!'
    else:
        return 'Извините, места на тренировке закончились'


@app.route("/delete_workout", methods=['POST'])
def delete_workout():
    if request.method == 'POST':

        user_id = request.form['user_id']
        workout_id = request.form['workout_id']
        visit_date = request.form['visit_date']

        try:
            # SQL-запрос для удаления тренировки по workout_id
            execute_query(f"""DELETE FROM "MEMBER_WORKOUT" WHERE "USER_ID" = '{user_id}' AND
            "WORKOUT_ID" = '{workout_id}' AND "VISIT_DATE" = '{visit_date}'""")

            execute_query(f"""UPDATE "WORKOUT" SET "REGISTERED_COUNT" = "REGISTERED_COUNT" - 1 
            WHERE "WORKOUT_ID" = '{workout_id}'""")

            # Перенаправляем пользователя обратно на страницу профиля
            return redirect(url_for('prof'))

        except psycopg2.Error as e:
            # Обработка ошибок, если что-то пошло не так при удалении тренировки
            print("Error while deleting workout:", e)

            return "Error while deleting workout. Please try again later."


@app.route("/memberships")
def memberships():

    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()

    # Получение данных из таблицы MEMBERSHIP
    cursor.execute("""SELECT * FROM "MEMBERSHIP" """)
    memberships_data = cursor.fetchall()

    cursor.close()
    connection.close()

    db_functions.delete_expired_memberships()
    your_memberships_data = your_memberships()

    return render_template('memberships.html', memberships_data=memberships_data,
                           your_memberships_data=your_memberships_data)


@app.route("/buy_membership/<int:membership_id>", methods=['POST'])
def buy_membership(membership_id):
    if request.method == 'POST':
        user_id = session.get('user_id')

        if user_id:

            membership_info = get_membership_info(membership_id)

            if membership_info:
                duration_months = membership_info.get('DURATION')
                start_date = datetime.now().date()
                end_date = start_date + relativedelta(months=duration_months)

                try:
                    # Добавляем информацию об абонементе для пользователя в таблицу MEMBER_MEMBERSHIP
                    execute_query(f"""INSERT INTO "MEMBER_MEMBERSHIP" ("USER_ID", "MEMBERSHIP_ID", "START_DATE", 
                    "END_DATE") VALUES ('{user_id}', '{membership_id}', '{start_date}', '{end_date}')""")

                    # После добавления абонемента перенаправляем пользователя на страницу абонементов
                    return redirect(url_for('memberships'))

                except errors.UniqueViolation as e:
                    message = "Вы уже приобрели такой абонемент и он еще не истек"
                    return jsonify({'error': message}), 400  # Возвращаем сообщение об ошибке в JSON


# Функция для получения информации о выбранном абонементе из базы данных
def get_membership_info(membership_id):
    connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                  database="FitnessClubDB")
    cursor = connection.cursor()
    cursor.execute(f"""SELECT * FROM "MEMBERSHIP" WHERE "MEMBERSHIP_ID" = '{membership_id}'""")
    membership_info = cursor.fetchone()
    cursor.close()
    connection.close()

    # Если информация о найденном абонементе доступна, возвращаем ее в виде словаря
    if membership_info:
        membership_dict = {
            "MEMBERSHIP_ID": membership_info[0],
            "DURATION": membership_info[1],
            "DESCRIPTION": membership_info[2],
            "COST": membership_info[3],
            "MEMBERSHIP_TYPE": membership_info[4]
        }
        return membership_dict


@app.route("/your_memberships")
def your_memberships():
    user_id = session.get('user_id')

    if user_id:

        connection = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                      database="FitnessClubDB")
        cursor = connection.cursor()

        # Запрос для получения информации о купленных абонементах пользователя
        cursor.execute(f"""SELECT MM."START_DATE", MM."END_DATE", M."MEMBERSHIP_TYPE", M."COST"
                           FROM "MEMBER_MEMBERSHIP" AS MM
                           JOIN "MEMBERSHIP" AS M ON MM."MEMBERSHIP_ID" = M."MEMBERSHIP_ID"
                           WHERE MM."USER_ID" = '{user_id}' """)

        your_memberships_data = cursor.fetchall()

        cursor.close()
        connection.close()

        return your_memberships_data


@app.route("/password_recovery", methods=['POST'])
def password_recovery():
    if request.method == 'POST':
        email = request.form['email']

        if db_functions.check_email_exists(email):

            session['reset_email'] = email
            return redirect(url_for('reset_password'))

        else:
            errors = ['Неверный email']
            return render_template('password_recovery.html', email=email, errors=errors)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        # Проверяем, есть ли email в сессии
        if 'reset_email' in session:
            return render_template('reset_password.html', email=session['reset_email'])
        else:
            # Если email отсутствует, перенаправляем на страницу входа
            return redirect(url_for('log_in'))

    elif request.method == 'POST':
        # Получаем новый пароль из формы
        new_password = request.form['new_password']
        new_password_confirmation = request.form['new_password_confirmation']
        # Получаем email из сессии
        email = session.get('reset_email')


        # Проверяем, есть ли email в сессии и новый пароль не пустой
        if email and new_password and db_functions.check_confirm_password(new_password, new_password_confirmation):
            hashed_password=bcrypt.generate_password_hash(new_password).decode('utf-8')
            # Обновляем пароль в базе данных
            execute_query(f"""UPDATE "USER" SET "PASSWORD" = '{hashed_password}' WHERE "USER_ID" = 
                             (SELECT "USER_ID" FROM "MEMBER" WHERE "MEMBER_EMAIL" = '{email}')""")

            # Очищаем email из сессии
            session.pop('reset_email', None)

            # Редиректим на страницу входа
            return redirect(url_for('log_in'))

        else:
            errors = []

            if not db_functions.check_password_len(new_password):
                errors.append('Некорректный пароль')
                errors.append('(длина от 8 до 25 символов)')
            elif not db_functions.check_password_symbols(new_password):
                errors.append('Пароль содержит')
                errors.append('недопустимые символы')
            elif not db_functions.check_confirm_password(new_password, new_password_confirmation):
                errors.append('Пароли не совпадают')

            return render_template('reset_password.html', new_password=new_password,
                                   new_password_confirmation=new_password_confirmation, errors=errors)


@app.route('/find_user', methods=['POST'])
def find_user():
    # Получение данных из формы
    username = request.form['username']

    generated_user_data = db_functions.generate_data_for_admin_user_list(username)

    # Возвращаем HTML-страницу с вставленными данными
    return render_template('admin_panel.html', show_view_user_form=True, username=username,
                           generated_user_data=generated_user_data)


@app.route('/delete_user', methods=['POST'])
def delete_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user = None
        if user_id.isdigit() and (0 <= int(user_id) <= 2147483647):
            conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                      database="FitnessClubDB")
            cursor = conn.cursor()

            cursor.execute(f"""SELECT "USER_ID" FROM "USER" WHERE "USER"."USER_ID" = '{user_id}';""")

            user = cursor.fetchone()

            cursor.close()
            conn.close()

    if not user:
        error = []
        error.append('user_id')
        return render_template('admin_panel.html',
                               user_id=user_id, show_user_delete_form=True, errors=error)
    else:
        execute_query(f"""DELETE FROM "USER" WHERE "USER_ID"='{user_id}';""")

        return render_template('admin_panel.html', delete_user_success=True)


@app.route('/find_trainer', methods=['POST'])
def find_trainer():
    # Получение данных из формы
    trainer_name = request.form['trainer_name']

    generated_trainer_data = db_functions.generate_data_for_admin_trainer_list(trainer_name)

    # Возвращаем HTML-страницу с вставленными данными
    return render_template('admin_panel.html', show_view_trainer_form=True, trainer_name=trainer_name,
                           generated_trainer_data=generated_trainer_data)


@app.route('/delete_trainer', methods=['POST'])
def delete_trainer():
    if request.method == 'POST':
        trainer_id = request.form['trainer_id']
        trainer = None

        if trainer_id.isdigit() and (0 <= int(trainer_id) <= 2147483647):
            conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                    database="FitnessClubDB")
            cursor = conn.cursor()

            cursor.execute(f"""SELECT "TRAINER_ID" FROM "TRAINER" WHERE "TRAINER_ID" = '{trainer_id}';""")

            trainer = cursor.fetchone()

            cursor.close()
            conn.close()

    if not trainer:
        errors = []
        errors.append('trainer_id')
        return render_template('admin_panel.html', trainer_id=trainer_id, show_trainer_delete_form=True, errors=errors)

    else:
        execute_query(f"""DELETE FROM "TRAINER" WHERE "TRAINER_ID"='{trainer_id}'""")

        return render_template('admin_panel.html', delete_trainer_success=True)


@app.route('/get_trainer_data', methods=['GET'])
def get_trainer_data():

    trainer_id = request.args.get('trainer_id')

    if trainer_id and db_functions.check_trainerId_in_db(trainer_id):
        trainer_data = db_functions.get_trainer_data_for_edit(trainer_id)
        return jsonify({'data': trainer_data, 'success': True})

    else:
        return jsonify({'success': False})


@app.route('/update_trainer', methods=['POST'])
def update_trainer():
    if request.method == 'POST':
        trainer_id = request.form['trainer_id']
        trainer_name = request.form['trainer_name']
        trainer_email = request.form['trainer_email']
        trainer_phone = request.form['trainer_phone']
        trainer_specialization = request.form['trainer_specialization']
        trainer_img = request.files['trainer_img']

        if trainer_img.filename != '':
            filename = secure_filename(trainer_img.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            trainer_img.save(file_path)

            # Обновление записи в таблице 'TRAINER' с использованием введенных данных
            execute_query(f"""UPDATE "TRAINER" SET 
                            "TRAINER_NAME" = '{trainer_name}', 
                            "TRAINER_EMAIL" = '{trainer_email}', 
                            "TRAINER_PHONE" = '{trainer_phone}', 
                            "TRAINER_SPECIALIZATION" = '{trainer_specialization}', 
                            "IMAGE_URL" = '{filename}' 
                            WHERE "TRAINER_ID" = '{trainer_id}' """)

            return render_template('admin_panel.html', update_trainer_success=True)

        else:
            # Обновление записи в таблице 'TRAINER' с использованием введенных данных
            execute_query(f"""UPDATE "TRAINER" SET 
                            "TRAINER_NAME" = '{trainer_name}', 
                            "TRAINER_EMAIL" = '{trainer_email}', 
                            "TRAINER_PHONE" = '{trainer_phone}', 
                            "TRAINER_SPECIALIZATION" = '{trainer_specialization}'
                            WHERE "TRAINER_ID" = '{trainer_id}' """)

        return render_template('admin_panel.html', update_trainer_success=True)


# Обработчик POST запроса для добавления тренера
@app.route('/add_trainer', methods=['POST'])
def add_trainer():
    if request.method == 'POST':

        trainer_name = request.form['add_trainer_name']
        trainer_email = request.form['trainer_email']
        trainer_phone = request.form['trainer_phone']
        trainer_specialization = request.form['trainer_specialization']
        trainer_img = request.files['trainer_img']

        filename = secure_filename(trainer_img.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        trainer_img.save(file_path)

        if not db_functions.check_trainer_email_exists(trainer_email) and\
                not db_functions.check_trainer_phone_exists(trainer_phone):

            execute_query(f"""INSERT INTO "TRAINER" ("TRAINER_NAME", "TRAINER_EMAIL", "TRAINER_PHONE", 
                        "TRAINER_SPECIALIZATION", "IMAGE_URL") VALUES ('{trainer_name}', '{trainer_email}', 
                        '{trainer_phone}', '{trainer_specialization}', '{filename}')""")

            return render_template('admin_panel.html', add_trainer_success=True)

        else:

            errors = []

            if db_functions.check_trainer_email_exists(trainer_email):
                errors.append('email')

            elif db_functions.check_trainer_phone_exists(trainer_phone):
                errors.append('phone')

        return render_template('admin_panel.html', add_trainer_name=trainer_name, trainer_email=trainer_email,
                               trainer_phone=trainer_phone, trainer_specialization=trainer_specialization,
                               errors=errors, show_add_trainer_form=True)



    else:
        return render_template('admin_panel.html', show_add_trainer_form=True)


@app.route('/find_workout', methods=['POST'])
def find_workout():
    # Получение данных из формы
    workout_name = request.form['workout_name']

    generated_workout_data = db_functions.generate_data_for_admin_workout_list(workout_name)

    # Возвращаем HTML-страницу с вставленными данными
    return render_template('admin_panel.html', show_view_workout_form=True, workout_name=workout_name,
                           generated_workout_data=generated_workout_data)


@app.route('/get_workout_data', methods=['GET'])
def get_workout_data():

    workout_id = request.args.get('workout_id')

    if workout_id and db_functions.check_workoutId_in_db(workout_id):
        workout_data = db_functions.get_workout_data_for_edit(workout_id)
        return jsonify({'data': workout_data, 'success': True})

    else:
        return jsonify({'success': False})


@app.route('/update_workout', methods=['POST'])
def update_workout():
    if request.method == 'POST':
        workout_id = request.form['update-workout_id']
        workout_name = request.form['workout_name']
        workout_description = request.form['workout_description']
        workout_max_participants = request.form['workout_max_participants']
        workout_cost = request.form['workout_cost']
        workout_schedule_string = request.form['workout_schedule']
        schedule_lines = workout_schedule_string.split('\n')  # Разбиваем строку на строки с парами "День": "Время"

        schedule_dict = {}
        errors = []
        for line in schedule_lines:
            if line.strip():
                day, time = map(str.strip, line.split(':', 1))

                if db_functions.validate_day_time(day, time):
                    schedule_dict[day.title()] = time

                else:

                    if not db_functions.validate_day_time(day, time):
                        errors.append('day_time')

        if 'day_time' not in errors:  # Проверка на наличие данных в словаре
            workout_schedule = json.dumps(schedule_dict)

            execute_query(f"""UPDATE "WORKOUT" SET 
                            "NAME" = '{workout_name}', 
                            "DESCRIPTION" = '{workout_description}', 
                            "MAX_PARTICIPANTS" = '{workout_max_participants}', 
                            "COST" = '{workout_cost}',
                            "WORKOUT_SCHEDULE" = '{workout_schedule}'
                            WHERE "WORKOUT_ID" = '{workout_id}' """)

            return render_template('admin_panel.html', update_workout_success=True)

        else:
            return render_template('admin_panel.html', workout_id=workout_id, workout_name=workout_name,
                                   workout_description=workout_description,
                                   workout_max_participants=workout_max_participants,
                                   workout_cost=workout_cost, workout_schedule=workout_schedule_string, errors=errors,
                                   show_update_workout_form=True)


@app.route('/add_workout', methods=['POST'])
def add_workout():
    if request.method == 'POST':

        trainer_id = request.form['trainer_id']
        add_workout_name = request.form['add_workout_name']
        workout_description = request.form['workout_description']
        workout_max_participants = request.form['workout_max_participants']
        workout_cost = request.form['workout_cost']
        schedule_string = request.form['workout_schedule']  # Получаем строку
        schedule_lines = schedule_string.split('\n')  # Разбиваем строку на строки с парами "День": "Время"

        if db_functions.check_trainerId_in_db(trainer_id):

            schedule_dict = {}

            for line in schedule_lines:

                if line.strip():
                    day, time = map(str.strip, line.split(':', 1))

                    if db_functions.validate_day_time(day, time):
                        schedule_dict[day.title()] = time

                    else:
                        errors = []
                        if not db_functions.validate_day_time(day, time):
                            errors.append('day_time')

            if schedule_dict:  # Проверка на наличие данных в словаре

                workout_schedule = json.dumps(schedule_dict)

                # Выполняем запрос в базу данных, используя workout_schedule
                execute_query(f"""INSERT INTO "WORKOUT" ("TRAINER_ID", "NAME", "DESCRIPTION", "MAX_PARTICIPANTS", 
                            "COST", "WORKOUT_SCHEDULE") VALUES ('{trainer_id}', '{add_workout_name.title()}',
                            '{workout_description}', '{workout_max_participants}', '{workout_cost}',
                            '{workout_schedule}'); """)

                return render_template('admin_panel.html', add_workout_success=True)

            else:

                return render_template('admin_panel.html', trainer_id=trainer_id, add_workout_name=add_workout_name,
                                       workout_description=workout_description,
                                       workout_max_participants=workout_max_participants,
                                       workout_cost=workout_cost, workout_schedule=schedule_string, errors=errors,
                                       show_add_workout_form=True)

        else:

            errors = []

            if not db_functions.check_trainerId_in_db(trainer_id):
                errors.append('trainer_id')

        return render_template('admin_panel.html', trainer_id=trainer_id, add_workout_name=add_workout_name,
                               workout_description=workout_description, workout_max_participants=workout_max_participants,
                               workout_cost=workout_cost, workout_schedule=schedule_string, errors=errors,
                               show_add_workout_form=True)

    else:
        return render_template('admin_panel.html', show_add_workout_form=True)


@app.route('/del_workout', methods=['POST'])
def del_workout():
    if request.method == 'POST':
        workout_id = request.form['workout_id']
        workout = None

        if workout_id.isdigit() and (0 <= int(workout_id) <= 2147483647):
            conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                    database="FitnessClubDB")
            cursor = conn.cursor()

            cursor.execute(f"""SELECT "WORKOUT_ID" FROM "WORKOUT" WHERE "WORKOUT_ID" = '{workout_id}';""")

            workout = cursor.fetchone()

            cursor.close()
            conn.close()

    if not workout:
        errors = []
        errors.append('workout_id')
        return render_template('admin_panel.html', workout_id=workout_id, show_workout_delete_form=True, errors=errors)

    else:
        execute_query(f"""DELETE FROM "WORKOUT" WHERE "WORKOUT_ID"='{workout_id}'""")

        return render_template('admin_panel.html', delete_workout_success=True)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


@app.route('/export_whole_database', methods=['POST'])
def export_whole_database():
    try:
        json_path = request.form['json_path']
        if os.path.exists(json_path) and os.path.isdir(json_path):

            conn = psycopg2.connect(user="postgres", password="Mkar7788", host="127.0.0.1", port="5432",
                                      database="FitnessClubDB")
            cursor = conn.cursor()

            # Получаем список всех таблиц в базе данных
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = cursor.fetchall()

            # Создаем пустой словарь для хранения данных всех таблиц
            database_data = {}

            # Перебираем все таблицы и получите их данные
            for table in tables:
                table_name = table[0]
                cursor.execute(f"""SELECT * FROM "{table_name}" """)
                table_data = cursor.fetchall()

                # Преобразуем данные в формат, удобный для преобразования в JSON
                export_data = []

                for row in table_data:
                    row_dict = {}
                    for i, column in enumerate(cursor.description):
                        column_name = column[0]
                        column_type = column[1]

                        # Если тип данных - Binary, преобразуйте его в строку
                        if column_type == Binary:
                            row_dict[column_name] = str(row[i], 'utf-8')
                        elif isinstance(row[i], (date, time, datetime)):
                            row_dict[column_name] = row[i].isoformat()
                        else:
                            row_dict[column_name] = row[i]

                    export_data.append(row_dict)

                # Добавляем данные таблицы к общему словарю
                database_data[table_name] = export_data

            # Преобразуем данные в JSON
            json_data = json.dumps({'data': database_data}, cls=CustomEncoder, ensure_ascii=False, indent=4)

            # Создаем объект ответа с правильными заголовками
            response = make_response(json_data)
            response.headers['Content-Disposition'] = 'attachment; filename=database_export.json'
            response.headers['Content-Type'] = 'application/json; charset=utf-8'

            # Сохраняем JSON-данные в файл на сервере
            with open(os.path.join(json_path, 'database_export.json'), 'w', encoding='utf-8') as file:
                file.write(json_data)

            return render_template('admin_panel.html', json_success=True)
        else:
            return render_template('admin_panel.html', show_json_form=True, errors=['json_path'], json_path=json_path)

    except Exception as e:
        return render_template('admin_panel.html')
    finally:
        # Закрываем соединение с базой данных
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn is not None:
            conn.close()


app.run(debug=True)


