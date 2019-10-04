FROM ropod/ropod_common:latest

RUN pip3 install --upgrade pip

RUN mkdir /mrta
COPY . /mrta
WORKDIR /mrta
RUN pip3 install -r requirements.txt && pip3 install -e .



