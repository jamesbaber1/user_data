import os
import sys
import shutil
import logging

# build the path to the freqtrade folder
freqtrade_folder = os.path.normpath(os.path.join(
    os.getcwd(),
    os.pardir,
    'freqtrade'
))

# stop any existing docker containers
os.system('powershell -Command "docker stop $(docker ps -aq)"')

# remove any existing docker containers
os.system('powershell -Command "docker rm $(docker ps -aq)"')

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

