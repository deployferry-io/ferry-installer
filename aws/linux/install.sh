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
apt install default-jdk
java -version
useradd --system --create-home ggc_user
groupadd --system ggc_group

curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip > greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller && rm greengrass-nucleus-latest.zip
java -jar ./GreengrassInstaller/lib/Greengrass.jar --version


/usr/bin/python3 -m pip install --user --upgrade pip
/usr/bin/python3 -m pip install invoke
/usr/bin/python3 -m pip install requests
/usr/bin/python3 -m pip install boto3

/usr/bin/python3 install.py $KEY

sudo -E java -Droot="/greengrass/v2" -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --init-config ./GreengrassInstaller/config.yaml \
  --component-default-user ggc_user:ggc_group \
  --setup-system-service true
