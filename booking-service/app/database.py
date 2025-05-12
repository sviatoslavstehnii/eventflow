from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
import redis
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

load_dotenv()

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://booking-redis:6379/0")

# Cassandra Configuration
CASSANDRA_HOSTS = os.getenv("CASSANDRA_HOSTS", "booking-db").split(",")

def get_redis():
    redis_client = redis.from_url(REDIS_URL)
    try:
        yield redis_client
    finally:
        redis_client.close()

def get_cassandra():
    logging.info(f"Connecting to Cassandra at hosts: {CASSANDRA_HOSTS}")
    
    # Create Cassandra cluster
    cluster = Cluster(CASSANDRA_HOSTS)
    session = cluster.connect()
    
    logging.info("Connected to Cassandra cluster")
    
    # Create keyspace if it doesn't exist
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS eventflow
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
    """)
    
    # Use the keyspace
    session.set_keyspace('eventflow')
    logging.info("Using keyspace: eventflow")
    
    # Create bookings table if it doesn't exist
    session.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id text PRIMARY KEY,
            event_id text,
            user_id text,
            status text,
            created_at timestamp,
            updated_at timestamp
        )
    """)
    logging.info("Ensured bookings table exists")
    
    # Create secondary indexes if they don't exist
    try:
        session.execute("""
            CREATE INDEX IF NOT EXISTS ON bookings (event_id)
        """)
        session.execute("""
            CREATE INDEX IF NOT EXISTS ON bookings (user_id)
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