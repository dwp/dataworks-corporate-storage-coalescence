FROM python:3-buster

ENV COALESCE_HOME=/coalescer
RUN mkdir $COALESCE_HOME
WORKDIR $COALESCE_HOME
COPY main.py ./
COPY utility ./utility
COPY requirements.txt ./
COPY run.sh ./
RUN pip install -r ./requirements.txt
RUN chmod +x ./main.py ./run.sh
ENTRYPOINT ["./run.sh"]
