from flask import Flask, render_template, request, url_for, flash
from flask_wtf import FlaskForm
from wtforms import DateField
from wtforms import SubmitField
from datetime import datetime
import httplib2
import googleapiclient.discovery
from config import Config
from oauth2client.service_account import ServiceAccountCredentials


app = Flask(__name__)
app.config.from_object(Config)

CREDENTIALS_FILE = 'test.json'
spreadsheet_id = 'key-document'

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive']
)
httpAuth = credentials.authorize(httplib2.Http())
service = googleapiclient.discovery.build('sheets', 'v4', http = httpAuth)


class DateForm(FlaskForm):
    data_apreensao = DateField('День рождения*', format='%d/%m/%Y')


@app.route('/', methods=['GET', 'POST'])
def widget():
    form = DateForm()
    
    if form.validate_on_submit():
        # Получить дату из формы и преобразовать в datetime
        date = datetime.strptime(request.form['data_apreensao'], '%d/%m/%Y')
        render_template('widget.html', form=form)
    
    if request.method == 'GET':
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A1:B5',
            majorDimension='ROWS'
        ).execute()
        
        doctor_times = []
        doctor_names = []
        for row in values['values'][1:]:
            if len(row) >= 3:  # Проверяем, что список row содержит хотя бы 3 элемента
                doctor_name = row[0]
                doctor_time = row[2]
                doctor_times.append(doctor_time)
                doctor_names.append(doctor_name)
                
        context = {
            'type_pet':['one', 'two'],
            'type_service':['tree', 'four', 'five'],
            'name_doctor': doctor_names,
            'time_doctor': doctor_times,
        }
        
        return render_template('widget.html', context=context)
    
    if request.method == 'POST':
        render_template('widget.html')


if __name__ == "__main__":
    app.run(debug=True)
