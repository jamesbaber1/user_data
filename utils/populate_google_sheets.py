from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import requests
import json
import string
import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1H1QHqXpz6SrlrUwSCzyGSX67c5y_Ap2uIAr1qRv9-g4'


def authorize(credentials_file):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    credentials = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return build('sheets', 'v4', credentials=credentials)


def get_values(service, field_range):
    # Call the Sheets API
    result = service.spreadsheets().values().get(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=field_range
    ).execute()
    return result.get('values', [])


def set_value(service, field_range, value):
    # Call the Sheets API
    result = service.spreadsheets().values().update(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        range=field_range,
        valueInputOption='RAW',
        body={'values': [[value]]}
    ).execute()
    return result.get('values', [])


def get_date(service, sheet):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d")
    time_column_values = get_values(service, f'{sheet}!A:A')

    if [current_time] != time_column_values[-1]:
        current_time_row = len(time_column_values) + 1
        set_value(service, f'{sheet}!A{current_time_row}', current_time)
        return current_time_row

    return len(time_column_values)


def get_bot_daily_profit(bot_name):
    response = requests.get('http://127.0.0.1:8080/api/v1/daily', auth=('Freqtrader', 'SuperSecret1!'))
    date = json.loads(response.text)[0][0]
    btc_daily_profit = json.loads(response.text)[0][1].replace(' BTC', '')
    return btc_daily_profit


def update_profit(service, sheet, bot_names, current_date_row):
    alphabet = dict(enumerate(string.ascii_uppercase, 1))

    for index, column_header in enumerate(get_values(service, sheet)[0], 1):

        for bot_name in bot_names:
            if bot_name in column_header:
                field_range = f'{sheet}!{alphabet[index]}{current_date_row}'
                # print(field_range)
                set_value(service, field_range, 'james')
                print(get_values(service, field_range)[-1])


if __name__ == '__main__':

    bot_names = [
        'Freqtrade_Bot_01',
        'Freqtrade_Bot_02',
        'Freqtrade_Bot_03',
        'Freqtrade_Bot_04',
        'Freqtrade_Bot_05',
     ]
    #
    # set_date('Sheet1!A:A')
    #
    #

    service = authorize('credentials.json')
    sheet = 'Sheet1'

    current_date_row = get_date(service, sheet)
    update_profit(service, sheet, bot_names, current_date_row)

    # print(get_values(service, 'Sheet1'))

    # column = dict(enumerate(string.ascii_uppercase, 1))
    # print(column[3])
    #
    #
    # print(set_values(service, 'Sheet1!A27', 'RAW', {'values': [[date]]}))
    #
    # print(date, btc_daily_profit)