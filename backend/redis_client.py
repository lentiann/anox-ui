import redis.asyncio as redis

redis_url = "rediss://default:AVNS_NCOH8RXCRTrfzv5JS0e@db-caching-fra1-71936-do-user-17488949-0.d.db.ondigitalocean.com:25061"

redis_client = redis.Redis(
    host="db-caching-fra1-71936-do-user-17488949-0.d.db.ondigitalocean.com",
    port=25061,
    password="AVNS_NCOH8RXCRTrfzv5JS0e",
    username="default",
    ssl=True,
    ssl_cert_reqs=None,
    # ssl_ca_certs='/path/to/ca-certificate.crt',
)
