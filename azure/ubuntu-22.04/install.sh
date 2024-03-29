while getopts k: flag
do
    case "${flag}" in
        k) KEY=${OPTARG};;
    esac
done
echo $KEY

## update and install packages
apt-get update && apt-get install -y python3 python3-pip unzip

wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

apt-get update && apt-get install -y moby-engine

touch /etc/docker/daemon.json

echo '{
  "log-driver": "local"
}' | tee /etc/docker/daemon.json

systemctl restart docker

apt-get update && apt-get install -y aziot-edge

mkdir -p /var/aziot/secrets
mkdir -p /var/secrets/aziot/identityd

/usr/bin/python3 install.py $KEY

iotedge config apply