while getopts k: flag
do
    case "${flag}" in
        k) KEY=${OPTARG};;
    esac
done
echo $KEY

## update and install packages
apt-get update
apt-get install python3 python3-pip unzip

wget https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm -O packages-microsoft-prod.rpm
sudo yum localinstall packages-microsoft-prod.rpm
rm packages-microsoft-prod.rpm

apt-get update
apt-get install moby-engine

touch /etc/docker/daemon.json

echo '{
  "log-driver": "local"
}' | tee /etc/docker/daemon.json

systemctl restart docker

apt-get update
apt-get install aziot-edge

mkdir -p /var/aziot/secrets
mkdir -p /var/secrets/aziot/identityd

/usr/bin/python3 install.py $KEY

iotedge config apply