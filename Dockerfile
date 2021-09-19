FROM python:3-onbuild
WORKDIR /usr/src/app
VOLUME data
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python" , "./kaktus.py" ]
