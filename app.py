from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, TelField
from wtforms.validators import DataRequired
import sqlite3, os, re, requests, json
from config import Config
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.config.from_object(Config)

class DateForm(FlaskForm):
    surname = StringField('Фамилия*', validators=[DataRequired()])
    name = StringField('Имя*', validators=[DataRequired()])
    patronymic = StringField('Отчество*', validators=[DataRequired()])
    phone = TelField('Телефон*', validators=[DataRequired()])
    birthday = DateField('День рождения*', format='%Y-%m-%d', validators=[DataRequired()])
    petname = StringField('Имя питомца*', validators=[DataRequired()])
    type_pet = StringField('Вид животного*', validators=[DataRequired()])
    doctor = SelectField('Доктор*', coerce=int, validators=[DataRequired()])
    type_service = StringField('Тип услуги*', validators=[DataRequired()])
    date = StringField('Дата записи*', validators=[DataRequired()])
    time = StringField('Время записи*', validators=[DataRequired()])
    submit = SubmitField('Записаться на прием')


def get_db_connection():
    try:
        db_path = os.path.abspath('doctor.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print("При подключении к базе данных произошла ошибка:", e)
        return None

def create_tables():
    try:
        with get_db_connection() as conn:
            with open("schema.sql", "r") as sq:
                conn.executescript(sq.read())
                cursor = conn.cursor()
                conn.commit()
    except sqlite3.Error as e:
        print("При создании таблиц произошла ошибка:", e)
    
def calculate_free_slots(start_time, end_time, booked_slots):
    try:
        start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

        free_slots = []
        current_time = start

        while current_time < end:
            is_booked = any(
                current_time >= slot['time'] and
                current_time < slot['time'] + timedelta(minutes=slot['duration'])
                for slot in booked_slots
            )
            
            if not is_booked:
                free_slots.append(current_time.strftime('%H:%M:%S'))
            current_time += timedelta(minutes=60)
            
        return free_slots

    except ValueError as e:
        print("Произошла ошибка при расчете свободных слотов:", e)
        return []

def add_appointment_to_json(file_path, new_data):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if 'Turtle' in data and isinstance(data['Turtle'], list):
                    data['Turtle'].append(new_data)
                else:
                    data['Turtle'] = [new_data]
        else:
            data = {'Turtle': [new_data]}
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print("An error occurred:", e)


@app.route('/', methods=['GET', 'POST'])
def widget():
    form = DateForm()
    pet = [
        "Собаки",
        "Кошки",
        "Птицы",
        "Грызуны",
        "Рептилии",
        "Пушистые звери",
        "Морские свинки"
    ]

    conn = get_db_connection()
    if not conn:
        flash('Ошибка подключения к базе данных', 'error')
        return redirect(url_for('widget'))

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT doctor_id, full_name_doc
            FROM (
                SELECT doctor_id, full_name_doc, 
                    CASE WHEN full_name_doc = 'Любой доктор' THEN 0 ELSE 1 END AS sort_order
                FROM doctors
                UNION
                SELECT 'any' AS doctor_id, 'Любой доктор' AS full_name_doc, 0 AS sort_order
            ) AS unique_doctors
            GROUP BY full_name_doc
            ORDER BY MIN(sort_order), full_name_doc
        """)
        doctors = []
        for row in cursor.fetchall():
            doctor_id, full_name_doc = row
            doctor_data = {
                'doctor_id': doctor_id,
                'full_name_doc': full_name_doc
            }
            doctors.append(doctor_data)

        form.doctor.choices = [(doctor['doctor_id'], doctor['full_name_doc']) for doctor in doctors]

        if request.method == 'POST' and form.validate_on_submit():
            selected_doctor_id = form.doctor.data
            date = form.date.data
            time = form.time.data
            selected_datetime = f"{date} {time}"

            cursor.execute("""
                SELECT doctor_id, full_name_doc
                FROM doctors
                WHERE full_name_doc != 'Любой доктор' AND start_date <= ? AND end_date >= ?
            """, (date, date))
            available_doctors = cursor.fetchall()

            free_doctors = []
            for doctor in available_doctors:
                doctor_id = doctor['doctor_id']
                booked_slots_query = conn.execute("""
                    SELECT time, duration 
                    FROM users 
                    WHERE doctor_id = ? AND DATE(time) = ?
                """, (doctor_id, date))
                booked_slots = [
                    {
                        'time': datetime.strptime(slot['time'], '%Y-%m-%d %H:%M:%S'),
                        'duration': slot['duration']
                    } for slot in booked_slots_query.fetchall()
                ]

                is_free = True
                selected_time = datetime.strptime(selected_datetime, '%Y-%m-%d %H:%M:%S')
                for slot in booked_slots:
                    slot_end_time = slot['time'] + timedelta(minutes=slot['duration'])
                    if slot['time'] <= selected_time < slot_end_time:
                        is_free = False
                        break

                if is_free:
                    free_doctors.append(doctor)

            if not free_doctors:
                flash('Нет свободных докторов в выбранное время', 'error')
                return redirect(url_for('widget'))

            selected_doctor = random.choice(free_doctors)
            doctor_id = selected_doctor['doctor_id']
            doctor_name = selected_doctor['full_name_doc']

            name = form.name.data
            surname = form.surname.data
            patronymic = form.patronymic.data
            phone = str(form.phone.data)
            birthday = form.birthday.data.strftime('%Y-%m-%d')
            petname = form.petname.data
            type_pet = form.type_pet.data
            type_service = form.type_service.data
            duration = 60

            user_data = {
                'lastname': surname,
                'firstname': name,
                'otchestvo': patronymic,
                'telephone': phone,
                'docname': doctor_name,
                'pettype': type_pet,
                'petname': petname,
                'datereg': date,
                'timereg': time
            }

            add_appointment_to_json('user_data.json', user_data)

            try:
                conn.execute("""
                    INSERT INTO users (name, pet, name_doc, doctor_id, time, duration) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"{name} {surname} {patronymic}", 
                    f"{petname} {type_pet}", 
                    doctor_name, 
                    doctor_id, 
                    selected_datetime, 
                    duration
                ))

                conn.execute("""
                    DELETE FROM users
                    WHERE doctor_id = 'any' AND DATE(time) = ? AND time = ?
                """, (date, selected_datetime))

                conn.commit()
                flash('Запись на прием успешно создана', 'success')
                return redirect(url_for('widget'))

            except sqlite3.Error as e:
                flash(f'Ошибка при обработке данных пользователя: {e}', 'error')

        if request.method == 'GET':
            return render_template('widget.html', form=form, doctors=doctors, pets=pet)

    except sqlite3.Error as e:
        flash('Ошибка при получении списка докторов из базы данных', 'error')

    finally:
        conn.close()

    return render_template('widget.html', form=form, doctors=doctors, pets=pet)   

@app.route('/get_free_slots/<int:doctor_id>', methods=['GET'])
def get_free_slots(doctor_id):
    conn = get_db_connection()
    current_date = datetime.now().date()
    if not conn:
        return jsonify({'error': 'Ошибка подключения к базе данных'})

    try:
        selected_doctor = conn.execute("SELECT full_name_doc FROM doctors WHERE doctor_id = ?", (doctor_id,)).fetchone()
        if not selected_doctor:
            return jsonify({'error': 'Врач не найден'})
        
        doctor_name = selected_doctor['full_name_doc']

        work_dates_query = conn.execute("SELECT DISTINCT start_date FROM doctors WHERE full_name_doc = ?", (doctor_name,))
        work_dates = [date['start_date'] for date in work_dates_query.fetchall()]

        free_slots = []

        for work_date_str in work_dates:
            work_date = datetime.strptime(work_date_str, '%Y-%m-%d').date()

            if work_date < current_date:
                continue
            doctor_info_query = conn.execute("SELECT start_time, end_time FROM doctors WHERE full_name_doc = ? AND start_date = ?", (doctor_name, work_date))
            doctor_info = doctor_info_query.fetchone()
            start_time = datetime.strptime(doctor_info['start_time'], '%H:%M:%S')
            end_time = datetime.strptime(doctor_info['end_time'], '%H:%M:%S')

            booked_slots_query = conn.execute("SELECT time, duration FROM users WHERE doctor_id = ? AND DATE(time) = ?", (doctor_id, work_date))
            booked_slots = [{'time': datetime.strptime(slot['time'], '%Y-%m-%d %H:%M:%S'), 'duration': slot['duration']} for slot in booked_slots_query.fetchall()]

            current_time = start_time
            slots = []
            while current_time < end_time:
                slot_end_time = current_time + timedelta(minutes=60)
                is_slot_booked = any(
                    current_time <= slot['time'] < slot_end_time or
                    (slot['duration'] is not None and current_time < slot['time'] + timedelta(minutes=slot['duration']) <= slot_end_time)
                    for slot in booked_slots
                )
                if not is_slot_booked:
                    if work_date == current_date and datetime.now().time() < current_time.time():
                        slots.append(current_time.strftime('%H:%M:%S'))
                    elif work_date != current_date:
                        slots.append(current_time.strftime('%H:%M:%S'))
                current_time = slot_end_time

            for booked_slot in booked_slots:
                booked_time = booked_slot['time']
                duration = booked_slot['duration']
                if duration is None:
                    continue
                booked_start_time = booked_time
                booked_end_time = booked_time + timedelta(minutes=duration)
                slots = [time_str for time_str in slots if not (booked_start_time <= datetime.strptime(f"{work_date_str} {time_str}", "%Y-%m-%d %H:%M:%S") < booked_end_time)]

            free_slots.append({'date': work_date_str, 'times': slots})

        services_query = conn.execute("SELECT * FROM positions WHERE posit_id = ?", (doctor_id,))
        services = [{'id': service['position_id'], 'name': service['service_doc']} for service in services_query.fetchall()]
        return jsonify({'free_slots': free_slots, 'services': services})

    except sqlite3.Error as e:
        print("Произошла ошибка при получении свободных слотов:", e)
        return jsonify({'error': 'Ошибка базы данных'})
    finally:
        conn.close()
        

def read_doctors_list_from_file(filename):
    doctors_list = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            doctors_list.append(line.strip())
    print(doctors_list)
    return doctors_list

doctors_list = read_doctors_list_from_file("doctor.txt")

def fill_doctors_data_from_json(data, db_file):
    create_tables()

    conn = get_db_connection()
    cursor = conn.cursor()

    assistants_hours = {}

    for entry in data['Turtle']:
        full_name = f"{entry['Name']} {entry['Surname']} {entry['Lastname']}".strip()
        date = entry['Date'].split('T')[0]
        time = entry['StartTime'].split('T')[1]
        start_date, start_time = date, time
        date = entry['Date'].split('T')[0]
        time = entry['EndTime'].split('T')[1]
        end_date, end_time = date, time

        if full_name in doctors_list:
            cursor.execute('''
                INSERT INTO doctors (full_name_doc, start_date, start_time, end_date, end_time)
                VALUES (?, ?, ?, ?, ?);
            ''', (full_name, start_date, start_time, end_date, end_time))
            conn.commit()
        else:
            if start_date in assistants_hours:
                assistants_hours[start_date]['end_time'] = end_time
            else:
                assistants_hours[start_date] = {
                    'start_time': start_time,
                    'end_time': end_time
                }

    for date, hours in assistants_hours.items():
        cursor.execute('''
            INSERT INTO doctors (full_name_doc, start_date, start_time, end_date, end_time)
            VALUES (?, ?, ?, ?, ?);
        ''', ('Ассистент ветеринарного врача', date, hours['start_time'], date, hours['end_time']))
        conn.commit()

    cursor.execute("""
    UPDATE users
    SET doctor_id = (
        SELECT d.doctor_id
        FROM doctors d
        WHERE d.full_name_doc = users.name_doc
    )
    """)
    conn.commit()

    cursor.execute("""
        SELECT DISTINCT start_date, start_time, end_time
        FROM doctors
    """)
    all_doctors_schedule = cursor.fetchall()

    for schedule in all_doctors_schedule:
        cursor.execute("""
            INSERT INTO doctors (full_name_doc, start_date, start_time, end_date, end_time)
            VALUES (?, ?, ?, ?, ?);
        """, ('Любой доктор', schedule['start_date'], schedule['start_time'], schedule['start_date'], schedule['end_time']))
        conn.commit()
        
        cursor.execute("""
    UPDATE positions
    SET posit_id = (
        SELECT d.doctor_id
        FROM doctors d
        WHERE d.full_name_doc = positions.names
    )
    """)
    conn.commit()

    conn.close()

def calculate_duration(start_time, end_time):
    start = datetime.strptime(start_time, '%H:%M:%S')
    end = datetime.strptime(end_time, '%H:%M:%S')
    duration = (end - start).seconds // 60  
    return duration if duration >= 60 else 60  
    
def process_json_and_store(data, db_file):
    create_tables()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    for entry in data['Turtle']:
        if 'LastnameTr' in entry:
            full_name_user = f"{entry['NameKl']} {entry['SurnameKl']} {entry['LastnameTr']}"
            name_doc = f"{entry['NameDoc']} {entry['SurnameDoc']} {entry['LastnameDoc']}"
            pet = entry['Pet']
            start_time = entry['StartDateTime'].split('T')[1]
            end_time = entry['EndDateTime'].split('T')[1]
            duration = calculate_duration(start_time, end_time)

        if name_doc in doctors_list:
            cursor.execute("SELECT doctor_id FROM doctors WHERE full_name_doc = ?", (name_doc,))
            doctor_id = cursor.fetchone()
            doctor_id = doctor_id[0] if doctor_id else None
        else:
            name_doc = 'Ассистент ветеринарного врача'
            cursor.execute("SELECT doctor_id FROM doctors WHERE full_name_doc = ?", (name_doc,))
            doctor_id = cursor.fetchone()
            doctor_id = doctor_id[0] if doctor_id else None

        if doctor_id:
            time = datetime.fromisoformat(entry['StartDateTime']).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO users (name, pet, doctor_id, name_doc, time, duration) VALUES (?, ?, ?, ?, ?, ?)",
                        (full_name_user, pet, doctor_id, name_doc, time, duration))
        else:
            print(f"Доктор {name_doc} не найден в базе данных.")

    conn.commit()
    conn.close()


@app.route('/webhook/1cTurtleobmen', methods=['POST', 'GET'])
def process_data_route():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'GET':
        user_data_file = 'user_data.json'
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as file:
                user_data = json.load(file)
            os.remove(user_data_file)
            return jsonify(user_data)
        else:
            return jsonify({}), 200

    if not request.json:
        return jsonify({'error': 'No JSON data provided'}), 400

    if request.method == "POST":
        json_data = request.json
        
        with open('received_data.json', 'w') as file:
            json.dump(json_data, file, ensure_ascii=False, indent=4)

        if 'Lastname' in json_data['Turtle'][0]:
            cursor.execute('DROP TABLE doctors')
            conn.commit()
            fill_doctors_data_from_json(json_data, 'doctor.db')
            conn.close()
            print('сработало заполнение1')
            return jsonify({'message': 'Data processed and stored successfully'}), 200
        elif 'LastnameTr' in json_data['Turtle'][0]:
            cursor.execute('DROP TABLE users')
            conn.commit()
            process_json_and_store(json_data, 'doctor.db')
            conn.close()
            print('сработало заоплнение2')
            return jsonify({'message': 'Data processed and stored successfully'}), 200
        

if __name__ == "__main__":
    create_tables()
    app.run(debug=True, port=5101)