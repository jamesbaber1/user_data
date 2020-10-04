import json
from utils import bot_sheet
import datetime

def lambda_handler(event, context):
    bot_sheet.update()
    return {
        'statusCode': 200,
        'body': json.dumps(f'At {datetime.datetime.utcnow().strftime("%Y-%m-%d")} the bot sheet was updated!')
    }