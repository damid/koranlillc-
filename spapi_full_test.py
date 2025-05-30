import os
import json
import logging
import requests
import boto3
from dotenv import load_dotenv
from botocore.auth import SigV4Auth
from botocore.credentials import Credentials
from botocore.awsrequest import AWSRequest
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

load_dotenv()

# Environment Variables
LWA_CLIENT_ID = os.getenv("LWA_CLIENT_ID")
LWA_CLIENT_SECRET = os.getenv("LWA_CLIENT_SECRET")
SP_API_REFRESH_TOKEN = os.getenv("SP_API_REFRESH_TOKEN")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
ROLE_ARN = os.getenv("ROLE_ARN")

REGION = "us-east-1"
MARKETPLACE_ID = "ATVPDKIKX0DER"
SKU = "RY104C-TF10A250V"

def get_access_token():
    logger.info("🔐 Access Token alınır...")
    url = "https://api.amazon.com/auth/o2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": SP_API_REFRESH_TOKEN,
        "client_id": LWA_CLIENT_ID,
        "client_secret": LWA_CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    res = requests.post(url, data=data, headers=headers)
    res.raise_for_status()
    logger.info("✅ Access Token alındı.")
    return res.json()["access_token"]

def assume_role():
    logger.info("🧾 AWS AssumeRole icra olunur...")
    sts_client = boto3.client("sts", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name=REGION)
    assumed_role = sts_client.assume_role(RoleArn=ROLE_ARN, RoleSessionName="sp-api-test-session")
    logger.info("✅ AWS tokenlər alındı.")
    return assumed_role["Credentials"]

def test_seller_api(access_token):
    logger.info("🔍 Sellers API test olunur...")
    url = "https://sellingpartnerapi-na.amazon.com/sellers/v1/marketplaceParticipations"
    headers = {"x-amz-access-token": access_token, "User-Agent": "SPAPI-Test/1.0"}
    res = requests.get(url, headers=headers)
    logger.info(f"Status: {res.status_code}")
    print(json.dumps(res.json(), indent=2))

def test_orders_api(access_token):
    logger.info("📦 Orders API test olunur...")
    url = f"https://sellingpartnerapi-na.amazon.com/orders/v0/orders?MarketplaceIds={MARKETPLACE_ID}&CreatedAfter=2024-01-01T00:00:00Z"
    headers = {"x-amz-access-token": access_token, "User-Agent": "SPAPI-Test/1.0"}
    res = requests.get(url, headers=headers)
    logger.info(f"Status: {res.status_code}")
    print(json.dumps(res.json(), indent=2))

def test_product_upload(access_token, credentials):
    logger.info("📤 Məhsul yükləmə testi başladılır...")
    url = f"https://sandbox.sellingpartnerapi-na.amazon.com/listings/2021-08-01/items/{SKU}?marketplaceIds=A2EUQ1WTGCTBG2"
    product_data = {
        "productType": "ELECTRONIC_COMPONENTS",
        "attributes": {
            "item_name": [{"value": "DF104S Sandbox Thermal Fuse 10A 250V"}],
            "brand": [{"value": "Cantherm"}],
            "manufacturer": [{"value": "Cantherm"}],
            "product_description": [{"value": "Sandbox test: Thermal protection fuse 10A 250V."}],
            "bullet_point": [{"value": "High temp protection"}, {"value": "Reliable circuit fuse"}],
            "main_image": [{"value": "https://via.placeholder.com/500"}],
            "manufacturer_part_number": [{"value": "DF104S"}],
            "standard_product_id": [{"value": "DF104S", "type": "MPN"}],
            "item_sku": [{"value": SKU}],
            "item_package_quantity": [{"value": 1}],
            "number_of_items": [{"value": 1}],
            "item_dimensions": {
                "length": [{"value": 4, "unit": "CM"}],
                "width": [{"value": 1, "unit": "CM"}],
                "height": [{"value": 1, "unit": "CM"}],
                "weight": [{"value": 0.01, "unit": "KG"}]
            },
            "msrp": [{"value": 1.00, "currency": "USD"}],
            "condition_type": [{"value": "new_new"}],
            "fulfillment_availability": [{"fulfillment_channel_code": "DEFAULT", "quantity": 10}]
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-amz-access-token": access_token,
        "User-Agent": "SPAPI-Test/1.0"
    }
    req = AWSRequest(method="PUT", url=url, data=json.dumps(product_data), headers=headers)
    aws_creds = Credentials(credentials['AccessKeyId'], credentials['SecretAccessKey'], credentials['SessionToken'])
    SigV4Auth(aws_creds, "execute-api", REGION).add_auth(req)
    res = requests.request(method=req.method, url=req.url, headers=dict(req.headers), data=req.body)
    logger.info(f"Status: {res.status_code}")
    print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    try:
        logger.info("\n=== SP-API Test Başladılır ===")
        token = get_access_token()
        creds = assume_role()
        test_seller_api(token)
        test_orders_api(token)
        test_product_upload(token, creds)
        logger.info("\n=== Test Tamamlandı ===")
    except Exception as e:
        logger.error(f"\n❌ Əsas xəta: {e}")
