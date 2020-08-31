import os
import sys
import shutil
import logging
from xml.etree import ElementTree


def update_runtime_configs():
    bot_name = input('Enter Test Bot Name(Freqtrade_Bot_01):\n') or 'Freqtrade_Bot_01'

    telegram_token = input('Enter Telegram Token(None):\n') or ''

    run_configurations_folder = os.path.normpath(os.path.join(
        os.getcwd(),
        os.pardir,
        '.idea',
        'runConfigurations'
    ))

    for run_configuration in os.listdir(run_configurations_folder):
        full_path = os.path.join(run_configurations_folder, run_configuration)
        tree = ElementTree.parse(full_path)
        root = tree.getroot()

        for configuration in root.findall('configuration'):
            for envs in configuration.findall('envs'):
                for env in envs.findall('env'):
                    if env.attrib['name'] == 'TEST_BOT':
                        env.set('value', bot_name)

                    if env.attrib['name'] == 'TELEGRAM_TOKEN':
                        env.set('value', telegram_token)

        tree.write(full_path)


def setup_freqtrade():
    # build the path to the freqtrade folder
    freqtrade_folder = os.path.normpath(os.path.join(
        os.getcwd(),
        os.pardir,
        'freqtrade'
    ))

    # stop any existing docker containers
    if sys.platform == 'win32':
        os.system('powershell -Command "If(docker ps -aq){docker stop $(docker ps -aq)}"')
    else:
        os.system('if [ $(docker ps -aq) ]; then docker stop $(docker ps -aq); fi')

    # remove any existing docker containers
    if sys.platform == 'win32':
        os.system('powershell -Command "If(docker ps -aq){docker rm $(docker ps -aq)}"')
    else:
        os.system('if [ $(docker ps -aq) ]; then docker rm $(docker ps -aq); fi')

    # make the user_data folder the current working directory
    os.chdir(os.path.join(os.getcwd(), os.pardir))

    # build full docker container with all the dependencies
    os.system('docker build --tag freqtradefull:latest .')

    # create the freqtrade folder
    if not os.path.exists(freqtrade_folder):
        os.mkdir(freqtrade_folder)

    # make the freqtrade folder the current working directory
    os.chdir(freqtrade_folder)

    # copy over the docker compose file
    shutil.copyfile('../docker-compose.yml', './docker-compose.yml')

    # create user directory structure
    failure = os.system('docker-compose run --rm freqtrade create-userdir --userdir user_data')
    if failure:
        logging.error(
            f'\nMake sure the folder where docker is accessing freqtrade is shared in your docker settings!\n'
            f'This guide will show you how to setup file sharing with docker '
            f'https://token2shell.com/howto/docker/sharing-windows-folders-with-containers/'
        )
        sys.exit(1)


if __name__ == '__main__':
    update_runtime_configs()
    setup_freqtrade()
