import os
import logging
import docker
from xml.etree import ElementTree
from utils import get_full_path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('setup')
logger.setLevel(logging.INFO)


def copy_runtime_configs():
    bot_name = input('Enter Test Bot Name(Freqtrade_Bot_01):\n') or 'Freqtrade_Bot_01'

    telegram_token = input('Enter Telegram Token(None):\n') or ''

    copy_runtime_config_path = os.path.normpath(os.path.join(
        os.getcwd(),
        os.pardir,
        '.idea',
        'runConfigurations',
        'copy.xml'
    ))

    tree = ElementTree.parse(copy_runtime_config_path)
    root = tree.getroot()

    for configuration in root.findall('configuration'):
        for envs in configuration.findall('envs'):
            for env in envs.findall('env'):
                if env.attrib['name'] == 'TEST_BOT':
                    env.set('value', bot_name)

                if env.attrib['name'] == 'TELEGRAM_TOKEN':
                    if telegram_token:
                        env.set('value', telegram_token)

    tree.write(copy_runtime_config_path)


def create_user_data_folder():
    logger.info('Creating freqtrade user data folder...')
    client = docker.from_env()
    client.containers.run(
        image="freqtradefull",
        command="create-userdir --userdir user_data",
        volumes={
            get_full_path(['freqtrade', 'user_data']): {
                'bind': '/freqtrade/user_data', 'mode': 'rw'}
        }
    )


def build_docker_image():
    logger.info('Building full freqtrade docker image...')
    client = docker.from_env()
    client.images.build(
        path=get_full_path(['']),
        dockerfile=r'./Dockerfile',
        tag='freqtradefull:latest',
        rm=True
    )


if __name__ == '__main__':
    copy_runtime_configs()
    build_docker_image()
    create_user_data_folder()
    logger.info('Setup completed successfully!')
