# from __future__ import print_function
import json
import pickle
import string
import os.path
import datetime
import logging

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from bot import Bot

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)
logging.getLogger('google').setLevel(logging.ERROR)


class BotSheet:
    def __init__(self, sheet_data, bots_data):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.spread_sheet_id = sheet_data['spread_sheet_id']
        self.service = self.authorize(sheet_data['credentials_file'])
        self.bots_data = bots_data
        self.sheet = sheet_data['sheet']
        self.get_current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    def authorize(self, credentials_file):
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
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.scopes)
                credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(credentials, token)

        return build('sheets', 'v4', credentials=credentials)

    def get_values(self, field_range):
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spread_sheet_id,
            range=field_range
        ).execute()
        return result.get('values', [])

    def set_value(self, field_range, value):
        result = self.service.spreadsheets().values().update(
            spreadsheetId=self.spread_sheet_id,
            range=field_range,
            valueInputOption='RAW',
            body={'values': [[value]]}
        ).execute()
        return result.get('values', [])

    def get_current_date_row(self):
        time_column_values = self.get_values(f'{self.sheet}!A:A')

        if self.get_current_date != time_column_values[-1][0]:
            current_time_row = len(time_column_values) + 1
            self.set_value(f'{self.sheet}!A{current_time_row}', self.get_current_date)
            return current_time_row

        return len(time_column_values)

    def update(self, section, response_data):
        # create a dictionary of the upper case numbers in the alphabet
        alphabet = dict(enumerate(string.ascii_uppercase, 1))

        for index, column_header in enumerate(self.get_values(self.sheet)[0], 1):

            for bot_name, value in response_data.items():
                if f'{bot_name.lower()}{section}' in column_header.lower().replace(' ', ''):
                    field_range = f'{self.sheet}!{alphabet[index]}{self.get_current_date_row()}'
                    self.set_value(field_range, float(value))


if __name__ == "__main__":
    with open('bots_config.json') as bots_config:
        data = json.load(bots_config)

    bot_sheet = BotSheet(data['sheet_data'], data['bots_data'])

    import time
    while True:
        for bot_data in data['bots_data']:
            bot = Bot(bot_data)

            print(bot.name)

            daily_data = bot.api_get('daily')
            print(daily_data)
            bot_sheet.update('daily', daily_data)

            balance_data = bot.api_get('balance_total')
            print(balance_data)
            bot_sheet.update('balance', balance_data)

        time.sleep(600)
