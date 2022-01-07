FROM python:3

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get update && apt-get install -y \
        bzr \
        cvs \
        git \
        mercurial \
        subversion \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.py /entrypoint.py
ENTRYPOINT ["python", "/entrypoint.py"]
