FROM python:3.11-bullseye
WORKDIR /code
COPY / .
RUN ls /code
RUN ls /code/src
RUN pip install -r requirements.txt
CMD [ "python", "./src/app.py" ]