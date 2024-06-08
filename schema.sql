CREATE TABLE IF NOT EXISTS doctors (
doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
full_name_doc TEXT,
start_date TEXT,
start_time TEXT,
end_date TEXT,
end_time TEXT
);

CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
name_doc TEXT,
pet TEXT,
doctor_id INTEGER,
time TEXT,
duration INTEGER,
FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
);

CREATE TABLE IF NOT EXISTS positions (
position_id INTEGER PRIMARY KEY AUTOINCREMENT,
names TEXT,
service_doc TEXT,
posit_id INTEGER,
FOREIGN KEY (posit_id) REFERENCES doctors(doctor_id)
);