import subprocess


def run_bash_command(command):
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    if error:
        return error.decode("utf-8")
    return output.decode("utf-8")


print(run_bash_command('ls'))

ssh -i LightsailDefaultKey-ap-northeast-1.pem ubuntu@13.230.112.72
cd freqtrade/user_data/strategies/
wget https://github.com/jamesbaber1/freqtrade_user_data/blob/master/strategies/TEMA_BB_RSI_Strategy01.py
