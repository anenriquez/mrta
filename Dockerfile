FROM ropod/ropod_common:latest

RUN git clone --single-branch --branch develop https://github.com/anenriquez/mrta_stn.git /opt/ropod/mrta_stn

WORKDIR /opt/ropod/mrta_stn

RUN pip3 install --upgrade pip && pip3 install -r requirements.txt && pip3 install -e .

