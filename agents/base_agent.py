import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseAgent:
    
    def __init__(self, name, description):
        self.name = name
        self.description = description
        logger.debug(f"Initializing {self.name}")
        
    def get_info(self):
        return {
            "name": self.name,
            "description": self.description,
            "commands": self.get_commands()
        }
    
    def get_commands(self):
        raise NotImplementedError("Subclasses must implement get_commands()")
    
    def execute(self, command, args):
        raise NotImplementedError("Subclasses must implement execute()")
