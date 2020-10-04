FROM freqtradeorg/freqtrade:master

RUN pip3 install -U -r requirements-plot.txt
RUN pip3 install -U -r requirements-hyperopt.txt
RUN pip3 install -U -r requirements.txt
RUN pip3 install psutil
