import sys
import os
import rapidjson
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_full_path(project_path):
    path = os.path.normpath(os.getcwd()).replace('\\', '/').split('/')
    if path:
        for index, folder in enumerate(path):
            if folder == 'user_data':
                path = path[:index + 1] + project_path
                break
        if sys.platform == 'win32':
            bots_config_path = f'{path[0]}\\'
        else:
            bots_config_path = f'{path[0]}/'
        for item in path:
            bots_config_path = os.path.join(
                bots_config_path,
                item
            )
        return bots_config_path


def get_config_values(project_path):
    config = get_full_path(project_path)
    print(config)
    with open(config) as file:
        config_values = rapidjson.load(file)

    return config_values


def get_bot_data(bot_config):
    for bot_data in bot_config['bots_data']:
        if bot_data['name'] == os.environ.get('TEST_BOT', 'Freqtrade_Bot_01'):
            return bot_data


def populate_config_values(config_name, screener_whitelist):
    print(config_name)
    test_config_path = get_full_path(['freqtrade', 'user_data', 'configs', config_name])
    config_values = get_config_values(['configs', config_name])
    bots_config = get_config_values(['bots_config.json'])
    bot_data = get_bot_data(bots_config)

    config_values['dry_run'] = bool(os.environ.get('DRY_RUN', bot_data['dry_run']))
    config_values['initial_state'] = bot_data['initial_state']
    config_values['exchange']['key'] = bot_data['exchange_key']
    config_values['exchange']['secret'] = bot_data['exchange_secret']
    config_values['telegram']['chat_id'] = bot_data['telegram_chat_id']
    config_values['telegram']['token'] = os.environ.get('TELEGRAM_TOKEN', bot_data['telegram_token'])
    config_values['api_server']['username'] = bot_data['api_server_username']
    config_values['api_server']['password'] = bot_data['api_server_password']

    if screener_whitelist:
        config_values['exchange']['pair_whitelist'] = screener_whitelist

    # create the configs folder if it doesn't exist
    configs_folder = os.path.dirname(test_config_path)
    print(configs_folder)
    if not os.path.exists(configs_folder):
        os.mkdir(configs_folder)

    # write the populate config file to disk
    with open(test_config_path, 'w') as file:
        rapidjson.dump(config_values, file, indent=2)


def copy_contents(source_folder, destination_folder):
    for file in os.listdir(source_folder):
        source_file = os.path.join(source_folder, file)
        destination_file = os.path.join(destination_folder, file)
        shutil.copyfile(source_file, destination_file)


def copy_credentials(parameters=None, screener_whitelist=None):
    logger.info('Copying over project files..')
    # copy over the strategies, hyperopts, and configs
    copy_contents(get_full_path(['hyperopts']), get_full_path(['freqtrade', 'user_data', 'hyperopts']))
    copy_contents(get_full_path(['strategies']), get_full_path(['freqtrade', 'user_data', 'strategies']))

    logger.info('Populating config credentials...')
    # populate configs with keys
    for _, _, configs in os.walk(get_full_path(['configs']), topdown=True):
        for config in configs:
            populate_config_values(config, screener_whitelist)


if __name__ == '__main__':
    # copy over the files, and populate the keys
    copy_credentials()
