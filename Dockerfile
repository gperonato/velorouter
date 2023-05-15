FROM python:3.10-slim
RUN apt-get update \
&& apt-get install -y --no-install-recommends \
gcc g++ libgdal-dev \
&& apt-get purge -y --auto-remove \
&& rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY . /velorouter
WORKDIR velorouter
CMD [ "gunicorn", "-b 0.0.0.0:8050", "app:server", "--workers 3", "--timeout 600"]