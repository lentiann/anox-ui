from env import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_SSL_CERT_REQS, REDIS_USERNAME
import redis.asyncio as redis

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_USERNAME,
    username=REDIS_PASSWORD,
    ssl=True,
    ssl_cert_reqs=REDIS_SSL_CERT_REQS,
    # ssl_ca_certs='/path/to/ca-certificate.crt',
)
