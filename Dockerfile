FROM ropod/ropod-base:fms

RUN pip3 install --upgrade pip
RUN mkdir -p /var/log/mrta
RUN chown -R $USER:$USER /var/log/mrta
RUN mkdir /mrta
COPY . /mrta
WORKDIR /mrta
RUN pip3 install -r requirements.txt && pip3 install -e .

RUN git clone https://github.com/anenriquez/mrta_planner.git /opt/mrs/planner
WORKDIR /opt/mrs/planner
RUN pip3 install -r requirements.txt && pip3 install -e .

RUN git clone https://github.com/anenriquez/mrta_datasets.git /opt/mrs/datasets
WORKDIR /opt/mrs/datasets
RUN pip3 install -r requirements.txt && pip3 install -e .

ENV TZ=CET
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENTRYPOINT ["/ros_entrypoint.sh"]


