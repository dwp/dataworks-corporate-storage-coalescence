FROM python:3-buster

ENV COALESCE_HOME=/coalescer
RUN mkdir $COALESCE_HOME
WORKDIR $COALESCE_HOME
COPY coalescer/main.py ./
COPY coalescer/utility ./utility
COPY coalescer/requirements.txt ./
RUN pip install -r ./requirements.txt
RUN chmod +x ./main.py
CMD ["./main.py"]
