import consul
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class ConsulClient:
    def __init__(self):
        self.consul_host = os.getenv("CONSUL_HOST", "consul")
        self.consul_port = int(os.getenv("CONSUL_PORT", "8500"))
        self.service_name = os.getenv("SERVICE_NAME", "notification-service")
        self.service_port = int(os.getenv("SERVICE_PORT", "8004"))
        self.consul = consul.Consul(host=self.consul_host, port=self.consul_port)

    def register_service(self):
        """Register the service with Consul"""
        try:
            self.consul.agent.service.register(
                name=self.service_name,
                service_id=f"{self.service_name}-{self.service_port}",
                address=self.service_name,
                port=self.service_port,
                tags=["api", "notifications"],
                check={
                    "http": f"http://{self.service_name}:{self.service_port}/health",
                    "interval": "10s",
                    "timeout": "5s"
                }
            )
            logger.info(f"Successfully registered {self.service_name} with Consul")
        except Exception as e:
            logger.error(f"Failed to register service with Consul: {str(e)}")
            raise

    def get_service(self, service_name: str):
        """Get service details from Consul"""
        try:
            _, services = self.consul.health.service(service_name, passing=True)
            if services:
                service = services[0]
                return {
                    "host": service["Service"]["Address"],
                    "port": service["Service"]["Port"]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get service {service_name} from Consul: {str(e)}")
            return None

    def deregister_service(self):
        """Deregister the service from Consul"""
        try:
            self.consul.agent.service.deregister(f"{self.service_name}-{self.service_port}")
            logger.info(f"Successfully deregistered {self.service_name} from Consul")
        except Exception as e:
            logger.error(f"Failed to deregister service from Consul: {str(e)}")
            raise 