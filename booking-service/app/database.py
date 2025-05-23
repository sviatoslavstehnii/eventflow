from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import redis
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'redis_booking')}:{os.getenv('REDIS_PORT', '6379')}/0")

CASSANDRA_HOSTS = os.getenv("CASSANDRA_HOSTS", "cassandra_booking").split(",")
CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "bookingkeyspace") # Added from compose

def get_redis():
    redis_client = redis.from_url(REDIS_URL)
    try:
        yield redis_client
    finally:
        redis_client.close()

def get_cassandra():
    logging.info(f"Connecting to Cassandra at hosts: {CASSANDRA_HOSTS}")
    
    cluster = Cluster(CASSANDRA_HOSTS)
    session = cluster.connect()
    
    logging.info("Connected to Cassandra cluster")
    
    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {CASSANDRA_KEYSPACE}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': '1'}}
    """)
    
    session.set_keyspace(CASSANDRA_KEYSPACE)
    logging.info(f"Using keyspace: {CASSANDRA_KEYSPACE}")
    
    # Create bookings table if it doesn't exist
    session.execute(f"""
        CREATE TABLE IF NOT EXISTS {CASSANDRA_KEYSPACE}.bookings (
            id text PRIMARY KEY,
            event_id text,
            user_id text,
            status text,
            created_at timestamp,
            updated_at timestamp
        )
    """)
    logging.info("Ensured bookings table exists")
    
    try:
        session.execute(f"""
            CREATE INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.bookings (event_id)
        """)
        session.execute(f"""
            CREATE INDEX IF NOT EXISTS ON {CASSANDRA_KEYSPACE}.bookings (user_id)
        """)
        logging.info("Ensured secondary indexes exist")
    except Exception as e:
        logging.warning(f"Index creation warning (can be ignored if indexes already exist): {str(e)}")
    
    try:
        yield session
    finally:
        logging.info("Closing Cassandra connection")
        session.shutdown()
        cluster.shutdown()