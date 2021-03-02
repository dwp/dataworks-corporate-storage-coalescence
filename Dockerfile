FROM python:3-buster

ENV COALESCE_HOME=/coalescer
RUN mkdir $COALESCE_HOME
WORKDIR $COALESCE_HOME
COPY coalescer/main.py ./
COPY coalescer/utility ./utility
COPY coalescer/requirements.txt ./
RUN pip install -r ./requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org --user
RUN chmod +x ./main.py
ENTRYPOINT ["python", "main.py"]
