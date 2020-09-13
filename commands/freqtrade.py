import sys
import os
import rapidjson
import shutil
import docker
import time
import pyperclip
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


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


def get_commands(parameters=None, screener_whitelist=None):
    if not parameters:
        parameters = sys.argv[1:]

    # copy over the strategies and hyperopts
    copy_contents(get_full_path(['hyperopts']), get_full_path(['freqtrade', 'user_data', 'hyperopts']))
    copy_contents(get_full_path(['strategies']), get_full_path(['freqtrade', 'user_data', 'strategies']))

    for index, parameter in enumerate(parameters, 0):
        if parameter in ['-c', '--config']:
            populate_config_values(parameters[index + 1], screener_whitelist)
            parameters[index + 1] = 'user_data/config.json'

    # set the current working directory to the freqtrade folder
    os.chdir(get_full_path(['freqtrade']))

    return ' '.join(parameters)


def run_docker_container(client, commands):
    container = client.containers.run(
        'freqtradefull', commands,
        working_dir=r'/freqtrade/',
        detach=True,
        volumes={get_full_path(['freqtrade', 'user_data']): {'bind': '/freqtrade/user_data', 'mode': 'rw'}}
    )
    previous_docker_logs = ''
    while client.containers.list():
        time.sleep(1)
        docker_logs = container.logs().decode("utf-8")
        output = docker_logs.replace(previous_docker_logs, '')
        if output:
            print(output)

        previous_docker_logs = docker_logs

    terminal_command = f"docker-compose run --rm freqtrade {commands}"

    logger.error(
        f"Run this command from the terminal in the ./freqtrade folder to see the full output:"
        f"\n\n{terminal_command}"
    )

    # copies the command to the clipboard
    pyperclip.copy(terminal_command)


def kill_all_containers(client):
    for container in client.containers.list():
        container.kill()


def main(parameters=None, screener_whitelist=None):
    # get the docker client
    client = docker.from_env()

    # kill any existing containers
    kill_all_containers(client)

    # copy over the files, populate the keys, then return the correct freqtrade commands
    commands = get_commands(parameters, screener_whitelist)

    # run the docker container with the commands
    run_docker_container(client, commands)


if __name__ == '__main__':
    main()
