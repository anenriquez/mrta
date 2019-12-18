FROM ropod/ropod-base:fms-test

WORKDIR /usr/src
RUN apt-get update \
    && apt-get install -y build-essential checkinstall \
    && apt-get install -y libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev \
    && wget https://www.python.org/ftp/python/3.5.9/Python-3.5.9.tgz \
    && tar xzf Python-3.5.9.tgz \
    && cd Python-3.5.9 \
    && ./configure --enable-optimizations \
    && make install \
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


