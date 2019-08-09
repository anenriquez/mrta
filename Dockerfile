FROM ropod/ropod_common:latest

RUN git clone --single-branch --branch develop https://github.com/anenriquez/mrta_stn.git /mrta_stn
WORKDIR /mrta_stn
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt && pip3 install -e .

RUN git clone --single-branch --branch develop https://github.com/anenriquez/mrta_datasets.git /mrta_datasets
WORKDIR /mrta_datasets
RUN pip3 install -e.

RUN mkdir /mrta
COPY . /mrta
WORKDIR /mrta
RUN pip3 install -r requirements.txt && pip3 install -e .

WORKDIR /mrta/mrs

CMD ["python3", "robot_proxy.py", "ropod_001"]


