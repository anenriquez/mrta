FROM ropod/ropod-base:fms

RUN pip3 install --upgrade pip
RUN mkdir -p /var/log/mrta
RUN chown -R $USER:$USER /var/log/mrta
RUN mkdir /mrta
COPY . /mrta
WORKDIR /mrta
RUN pip3 install -r requirements.txt && pip3 install -e .

ENTRYPOINT ["/ros_entrypoint.sh"]


