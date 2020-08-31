### Getting Started

If you don't have it already download and install Python [here](https://www.python.org/downloads/). 

If you don't have it already download and install PyCharm Community Edition [here](https://www.jetbrains.com/pycharm/download/). 

Open Pycharm and create a new project by cloning this git repo address.

With the terminal inside the project root directory install the dependencies by running:

``pip install -r requirements.txt``

Follow the instructions for installing docker on your machine [here](https://docs.docker.com/get-docker/).

Create a docker account [here](https://hub.docker.com/signup/) if you haven't already.

Setup file sharing for the `freqtrade` folder inside the root of this repo by going to Docker Desktop and then
`Settings > Resources > File Sharing` Then add the path to your freqtrade folder in your project. This allows docker to 
create files here.

Your path might look something like this:  
`C:\Users\<your username>\PycharmProjects\user_data\freqtrade`

Copy the `example_bots_config.json` and rename it to `bots_config.json`. Then fill out all those values for each of your
bots.

Optional: If you want to test on a bot, create a new bot in telegram and assign its token to the `TELEGRAM_TOKEN` environment
variable in each of your runtime configurations.

Then in PyCharm in your runtime configurations select `utils > setup` and click the play button to run it.

Freqtrade is now setup and you can run the other configuration commands and any of the other commands listed on:
[freqtrade.io](freqtrade.io)



