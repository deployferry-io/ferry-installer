import sys
import requests
import json

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
    return data["access_token"], data["registration_id"]


def get_azure_certs(token: str):
    response = requests.post(API_URL + "/registration/azure/get_certificate",
                 headers={
                     "Authorization": f"Bearer {token}",
                     "accept": "application / json"
                 },
                 data=json.dumps({}))

    if not response.ok:
        raise Exception(f"Unable to get AWS Credentials with response code {response.status_code}")
    return response.json()


key = sys.argv[1]

token, registration_id = get_bearer_token(key)

provisioning_details = get_azure_certs(token)

with open(f"/var/aziot/secrets/{registration_id}.pem", "w") as f:
    f.write(provisioning_details["full_chain"])

with open(f"/var/aziot/secrets/{registration_id}.key.pem", "w") as f:
    f.write(provisioning_details["private_key"])

with open(f"/var/secrets/aziot/identityd/dps-additional-data.json", "w") as f:
    f.write(json.dumps(provisioning_details["device_payload"]))

provisioning_host = provisioning_details["provisioning_host"]
id_scope = provisioning_details["id_scope"]

edge_config = """
[provisioning]
source = "dps"
global_endpoint = "https://{provisioning_host}"
id_scope = "{id_scope}"

 payload = {{ uri = "file:///var/secrets/aziot/identityd/dps-additional-data.json" }}

[provisioning.attestation]
method = "x509"
registration_id = "{registration_id}"

# Identity certificate private key
identity_pk = "file:///var/aziot/secrets/{registration_id}.key.pem"

# Identity certificate
identity_cert = "file:///var/aziot/secrets/{registration_id}.pem" """.format(
    provisioning_host=provisioning_host,
    id_scope=id_scope,
    registration_id=registration_id)

with open("/etc/aziot/config.toml", "w") as f:
    f.write(edge_config)
