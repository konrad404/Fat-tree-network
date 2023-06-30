cd netbox-docker-with-plugins

if [ ! -d "netbox-docker" ]; then
  git clone -b release https://github.com/netbox-community/netbox-docker.git
fi

cd netbox-docker

tee docker-compose.override.yml <<EOF
version: '3.4'
services:
  netbox:
    ports:
      - 8000:8080
    build:
      context: .
      dockerfile: Dockerfile-Plugins
    image: netbox:latest-plugins
  netbox-worker:
    image: netbox:latest-plugins
    build:
      context: .
      dockerfile: Dockerfile-Plugins
  netbox-housekeeping:
    image: netbox:latest-plugins
    build:
      context: .
      dockerfile: Dockerfile-Plugins
EOF

# visualization plugin
tee plugin_requirements.txt <<EOF
netbox-topology-views
EOF

sed -i 's/# PLUGINS = \[\]/PLUGINS = \[\"netbox_topology_views\"\]/g' configuration/configuration.py

tee Dockerfile-Plugins <<EOF
FROM netboxcommunity/netbox:latest

COPY ./plugin_requirements.txt /
RUN /opt/netbox/venv/bin/pip install  --no-warn-script-location -r /plugin_requirements.txt

# These lines are only required if your plugin has its own static files.
COPY configuration/configuration.py /etc/netbox/config/configuration.py
COPY configuration/plugins.py /etc/netbox/config/plugins.py

USER root
RUN mkdir -p /opt/netbox/netbox/static/netbox_topology_views/img
# RUN SECRET_KEY="dummyKeyWithMinimumLength-------------------------" /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate netbox_topology_views
# RUN SECRET_KEY="dummyKeyWithMinimumLength-------------------------" /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py collectstatic --no-input
EOF

# build
docker compose build --no-cache

# start
docker compose pull
docker compose up -d

# run commands inside docker to fully load the plugin
CONTAINER_ID=$(docker ps -f="expose=8080" | awk '{ print $1 }' | tail -n 1)
docker exec -u root -it $CONTAINER_ID bash -c "SECRET_KEY="dummyKeyWithMinimumLength-------------------------" /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py migrate netbox_topology_views"
docker exec -u root -it $CONTAINER_ID bash -c "SECRET_KEY="dummyKeyWithMinimumLength-------------------------" /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py collectstatic --no-input"
