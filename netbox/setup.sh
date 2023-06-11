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
EOF

docker compose pull
docker compose up -d

until docker-compose exec netbox /opt/netbox/netbox/manage.py migrate &>/dev/null; do
  sleep 1
done

docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser