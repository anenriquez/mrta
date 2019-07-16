FROM ropod/ropod_common:latest

RUN git+ssh://git@github.com/anenriquez/mrta_stn.git@develop#egg=mrta_stn opt/ropod/mrta_stn
WORKDIR /opt/ropod/mrta_stn

RUN pip3 install --upgrade pip && pip3 install -r requirements.txt && pip3 install -e .

