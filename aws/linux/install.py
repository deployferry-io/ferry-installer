import sys
import os
import requests
import boto3
import json
from urllib.request import urlopen


#### utils
def recursive_sort(data):
    if isinstance(data, list):
        for item in data:
            recursive_sort(item)
        data.sort(key=lambda x: str(x))
    if isinstance(data, dict):
        for value in data.values():
            recursive_sort(value)


def download_file_from_url(url, filepath):
    # download file from url and persist it into filepath
    data = urlopen(url=url)
    with open(filepath, "wb") as local_file:
        local_file.write(data.read())


# context manager that guarantees switching back to original directory when outside the context
class ChangeDirectory:

    def __init__(self, new_path):
        self.new_path = os.path.expanduser(new_path)

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.saved_path)


API_URL = "https://api.deployferry.io"


def get_bearer_token(key: str):
    response = requests.post(API_URL + "/auth/login_node",
                 headers={
                     "accept": "application / json"
                 },
                data=json.dumps({
                     "token": key,
                 }))

    if not response.ok:
        raise Exception(f"Unable to get credentials with response code {response.status_code}")
    data = response.json()
    return data["access_token"]


def get_aws_session(token: str):
    response = requests.get(API_URL + "/registration/aws/credentials",
                 headers={
                     "Authorization": f"Bearer {token}",
                     "accept": "application / json"
                 })

    if not response.ok:
        raise Exception(f"Unable to get AWS Credentials with response code {response.status_code}")
    return response.json()


def post_certificate_arn(token: str, certificate_arn: str):
    response = requests.post(API_URL + "/registration/aws/attach_policy_to_certificate",
                             headers={
                                 "Authorization": f"Bearer {token}",
                                 "accept": "application / json"
                             },
                             data=json.dumps({
                                 "certificate_arn": certificate_arn,
                             }))

    if not response.ok:
        raise Exception(f"Unable to post certificate {response.status_code} {response.json()}")
    return response.json()


### load our device configuration from the API, fetch relevant components and install them.
key = sys.argv[1]

bearer_token = get_bearer_token(key=key)

credentials = get_aws_session(token=bearer_token)

iot_client = boto3.client(
    'iot',
    aws_access_key_id=credentials["access_key_id"],
    aws_secret_access_key=credentials["secret_key_id"],
    aws_session_token=credentials["session_token"],
    region_name=credentials["region"]
)

## create a certificate and key pair
certificates = iot_client.create_keys_and_certificate(setAsActive=True)

node_configuration = post_certificate_arn(token=bearer_token, certificate_arn=certificates["certificateArn"])


### with everything setup -- its time to save our certs!
CERT_KEY_DIR = "greengrass/certs/"
CERT_PEM_FILE_FORMAT = "{}.pem.crt"
PRIV_KEY_FILE_FORMAT = "{}.pem.key"
ROOT_CA_FILE = "root.ca.pem"

KEY_CERT_ID = "certificateId"
KEY_CERT_ARN = "certificateArn"
KEY_THING_ARN = "thingArn"
KEY_POLICY_NAME = "policyName"
KEY_CERT_PEM = "certificatePem"
KEY_KEY_PAIR = "keyPair"
KEY_PRIV_KEY = "PrivateKey"
ATS_ROOT_CA_RSA_2048_REMOTE_LOATION = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"


cert_key_full_dir_path = os.path.join("/", CERT_KEY_DIR)
if not os.path.exists(cert_key_full_dir_path):
    os.makedirs(cert_key_full_dir_path)

with ChangeDirectory(cert_key_full_dir_path):
    file_prefix = certificates[KEY_CERT_ID][:10]
    cert_file = CERT_PEM_FILE_FORMAT.format(file_prefix)
    key_file = PRIV_KEY_FILE_FORMAT.format(file_prefix)

    # owner read/write, group and others read-only
    with os.fdopen(os.open(cert_file, os.O_CREAT | os.O_WRONLY, 0o644), 'w') as cf:
        cf.write(certificates["certificatePem"])
        KEY_CORE_CERT_FILE_LOCATION = os.path.join(cert_key_full_dir_path, cert_file)

    # owner read/write, group and others no permission, as this is **private key**
    with os.fdopen(os.open(key_file, os.O_CREAT | os.O_WRONLY, 0o600), 'w') as kf:
        kf.write(certificates["keyPair"]["PrivateKey"])
        KEY_CORE_PRIV_KEY_FILE_LOCATION = os.path.join(cert_key_full_dir_path, key_file)

    # owner read/write, group and others read-only
    download_file_from_url(url=ATS_ROOT_CA_RSA_2048_REMOTE_LOATION, filepath=ROOT_CA_FILE)
    os.chmod(ROOT_CA_FILE, 0o644)
    KEY_ROOT_CA_FILE_LOCATION = os.path.join(cert_key_full_dir_path, ROOT_CA_FILE)


config = f"""
---
system:
  certificateFilePath: "{KEY_CORE_CERT_FILE_LOCATION}"
  privateKeyPath: "{KEY_CORE_PRIV_KEY_FILE_LOCATION}"
  rootCaPath: "{KEY_ROOT_CA_FILE_LOCATION}"
  rootpath: "/greengrass/v2"
  thingName: "{node_configuration["name"]}"
services:
  aws.greengrass.Nucleus:
    componentType: "NUCLEUS"
    version: "2.9.0"
    configuration:
      awsRegion: "{node_configuration["region"]}"
      iotRoleAlias: "{node_configuration["iotRoleAlias"]}"
      iotDataEndpoint: "{node_configuration["iotDataEndpoint"]}"
      iotCredEndpoint: "{node_configuration["iotCredEndpoint"]}"
"""
with open("GreengrassInstaller/config.yaml", 'w') as cf:
    cf.write(config)

