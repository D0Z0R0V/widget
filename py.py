from pprint import pprint
import httplib2
import googleapiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials

CREDENTIALS_FILE = 'test.json'
spreadsheet_id = '1HIeAyUK99XK2rCFSCfzWZBQiXxn-8kJ3HTmZzx3AT0c'

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive']
)
httpAuth = credentials.authorize(httplib2.Http())
service = googleapiclient.discovery.build('sheets', 'v4', http = httpAuth)

# Получение данных из файла
value = service.spreadsheets().values().get(
    spreadsheetId=spreadsheet_id,
    range='A1:C4',
    majorDimension='ROWS'
).execute()
'''
# Извлечение времени работы для всех врачей
times_of_work = {}
for row in value['values'][1:]:  # Пропускаем первую строку с заголовками
    if len(row) >= 3:  # Проверяем, что список row содержит хотя бы 3 элемента
        times_of_work[row[0]] = row[2]'''
        
doctor_times = []
doctor_names = []
for row in value['values'][1:]:  # Пропускаем первую строку с заголовками
    if len(row) >= 3:  # Проверяем, что список row содержит хотя бы 3 элемента
        doctor_name = row[0]
        doctor_time = row[2]
        doctor_times.append(doctor_time)
        doctor_names.append(doctor_name)


pprint(doctor_times)
pprint(doctor_names)
exit()

# Пример записи в файл
values = service.spreadsheets().values().batchUpdate(
    spreadsheetId=spreadsheet_id,
    body={
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": "B3:C4",
             "majorDimension": "ROWS",
             "values": [["number B3", "Number C3"], ["Number B4", "Number C4"]]},
            {"range": "D5:E6",
             "majorDimension": "COLUMNS",
             "values": [["Number D5", "Number D6"], ["Number E5", "Number E6"]]}
	]
    }
).execute()