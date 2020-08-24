import sys
import os
import rapidjson
import shutil
import subprocess
from subprocess import CalledProcessError


def get_full_path(project_path):
    path = os.path.normpath(os.getcwd()).replace('\\', '/').split('/')
    if path:
        for index, folder in enumerate(path):
            if folder == 'user_data':
                path = path[:index+1] + project_path
                break
        bots_config_path = f'{path[0]}\\'
        for item in path:
            bots_config_path = os.path.join(
                bots_config_path,
                item
            )
        return bots_config_path


def get_bot_config_values(project_path):
    bots_config = get_full_path(['utils', 'bots_config.json'])
    with open(bots_config) as file:
        config_values = rapidjson.load(file)

    return config_values


def get_config_values(project_path):
    bots_config = get_full_path(project_path)
    with open(bots_config) as file:
        config_values = rapidjson.load(file)

    return config_values


def get_bot_data(bot_config):
    for bot_data in bot_config['bots_data']:
        if bot_data['name'] == os.environ.get('TEST_BOT', 'Freqtrade_Bot_01'):
            return bot_data


def populate_config_values(config_name, screener_whitelist):
    test_config_path = get_full_path(['freqtrade', 'user_data', 'config.json'])
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

    with open(test_config_path, 'w') as file:
        rapidjson.dump(config_values, file, indent=2)


def copy_contents(source_folder, destination_folder):
    for file in os.listdir(source_folder):
        source_file = os.path.join(source_folder, file)
        destination_file = os.path.join(destination_folder, file)
        shutil.copyfile(source_file, destination_file)


def main(parameters=None, screener_whitelist=None):

    if not parameters:
        parameters = sys.argv[1:]

    # copy over the strategies and hyperopts
    copy_contents(get_full_path(['hyperopts']), get_full_path(['freqtrade', 'user_data', 'hyperopts']))
    copy_contents(get_full_path(['strategies']), get_full_path(['freqtrade', 'user_data', 'strategies']))

    for index, parameter in enumerate(parameters, 0):
        if parameter in ['-c', '--config']:
            populate_config_values(parameters[index+1], screener_whitelist)
            parameters[index+1] = 'user_data/config.json'

    # set the current working directory to the freqtrade folder
    os.chdir(get_full_path(['freqtrade']))

    # run freqtrade
    commands = ' '.join(['docker-compose', 'run', '--rm', 'freqtrade'] + parameters)

    # get the path to the log file
    log_file_path = get_full_path(['freqtrade', 'user_data', 'logs', 'commands.log'])

    # remove the log file if needed
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # run the freqtrade docker process and wrote the output to a log file
    log_file = open(log_file_path, "w")
    if os.system(commands) != 0:
        try:
            subprocess.check_call(commands, stderr=log_file)

        except CalledProcessError as error:
            raise RuntimeError(error)

        finally:
            log_file.close()


if __name__ == '__main__':
    main()