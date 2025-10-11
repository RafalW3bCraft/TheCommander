import os

class Config:
    SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-key")
    
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
    
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    
    HOST = "0.0.0.0"
    PORT = 5000
    
    @classmethod
    def validate_required_keys(cls):
        missing_keys = []
        if not cls.ANTHROPIC_API_KEY:
            missing_keys.append("ANTHROPIC_API_KEY")
        
        if missing_keys:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
        
        return True
