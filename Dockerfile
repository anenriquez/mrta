FROM ropod/ropod-base:fms

WORKDIR /usr/src
RUN wget https://www.python.org/ftp/python/3.5.9/Python-3.5.9.tgz \
    && sudo tar xzf Python-3.5.9.tgz \
    && cd Python-3.5.9 \
    && sudo ./configure --enable-optimizations \
    && sudo make install \
    && pip3 install --upgrade pip

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

ENTRYPOINT ["/ros_entrypoint.sh"]


