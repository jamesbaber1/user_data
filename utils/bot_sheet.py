# from __future__ import print_function
import json
import pickle
import string
import os.path
import datetime
import logging
import time

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
        self.current_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        self.date_rows = {}

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

    def set_current_date(self, date_column_values):
        if self.current_date != date_column_values[-1]:
            current_date_row = len(date_column_values) + 2
            self.set_value(f'{self.sheet}!A{current_date_row}', self.current_date)

    def get_date_rows(self, dates):
        date_column = self.get_values(f'{self.sheet}!A:A')
        date_column_values = [row[0] for row in date_column][1:]

        for date in dates:
            if date not in date_column_values:
                self.set_current_date(date_column_values)

        for row, date in enumerate(date_column_values, 2):
            self.date_rows[date] = row

        return self.date_rows

    def get_daily_profit(self, bot_instance):
        daily_profit = {}
        response_data = bot_instance.api_get('daily')
        config = bot_instance.api_get('show_config')
        
        if response_data and config:
            for date, stake_currency, _, _ in response_data:
                stake_currency_amount = float(stake_currency.replace(f' {config["stake_currency"]}', ''))

                if round(stake_currency_amount, 8) != 0.0000000:
                    daily_profit[date] = stake_currency_amount

        return daily_profit

    def get_total_balance(self, bot_instance):
        total_balance = None
        response_data = bot_instance.api_get('balance')
        if response_data:
            total_balance = float(response_data['total'])

        return total_balance

    def update_daily(self, bot_instance):
        # create a dictionary of the upper case numbers in the alphabet
        alphabet = dict(enumerate(string.ascii_uppercase, 1))
        daily_profit = self.get_daily_profit(bot_instance)
        date_rows = self.get_date_rows(daily_profit.keys())

        print(date_rows)
        if daily_profit:
            for index, column_header in enumerate(self.get_values(self.sheet)[0], 1):
                for date, profit in daily_profit.items():
                    row = date_rows.get(date)
                    if row:
                        if f'{bot_instance.name.lower()}{"daily"}' in column_header.lower().replace(' ', ''):
                            field_range = f'{self.sheet}!{alphabet[index]}{row}'
                            self.set_value(field_range, profit)

    def update_balance(self, bot_instance):
        # create a dictionary of the upper case numbers in the alphabet
        alphabet = dict(enumerate(string.ascii_uppercase, 1))
        balance = self.get_total_balance(bot_instance)

        print(self.date_rows)

        if balance:
            for index, column_header in enumerate(self.get_values(self.sheet)[0], 1):
                if f'{bot_instance.name.lower()}{"balance"}' in column_header.lower().replace(' ', ''):
                    row = self.date_rows.get(self.current_date)
                    if row:
                        field_range = f'{self.sheet}!{alphabet[index]}{row}'
                        self.set_value(field_range, balance)


if __name__ == "__main__":

    while True:
        with open('bots_config.json') as bots_config:
            data = json.load(bots_config)

        bot_sheet = BotSheet(data['sheet_data'], data['bots_data'])
        for bot_data in data['bots_data']:
            bot = Bot(bot_data, data['bot_alerts'])

            try:
                print(bot.name)
                bot_sheet.update_daily(bot)

                bot_sheet.update_balance(bot)

            except Exception as error:
                bot.report_error(str(error))

        time.sleep(300)

