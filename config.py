"""
Configuration module for SVG to TGS Telegram Bot
Handles environment variables and bot settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration class containing all bot settings"""
    
    def __init__(self):
        # Bot configuration
        self.bot_token = os.getenv("8435159197:AAEjiiGpPdpmtDR9dasKWbTDHHJkk4gXZUA")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # API configuration
        self.api_id = os.getenv("API_ID")
        
        # Admin configuration
        self.owner_id = int(os.getenv("OWNER_ID", 0)) if os.getenv("OWNER_ID") else None
        
        # File processing limits
        self.max_file_size = 5 * 1024 * 1024  # 5MB in bytes
        self.required_svg_size = (512, 512)  # Required SVG dimensions
        self.max_batch_size = 15  # Maximum files in batch processing
        
        # Processing timeouts
        self.processing_delay = 3  # Initial delay in seconds
        self.batch_timeout = 300  # 5 minutes timeout for batch processing
        
        # Conversion settings
        self.output_width = 512
        self.output_height = 512
        self.output_fps = 60
        
        # Admin settings
        self.max_broadcast_length = 4096  # Telegram message limit
    
    @property
    def is_production(self):
        """Check if running in production environment"""
        return bool(os.getenv('RENDER') or os.getenv('HEROKU_APP_NAME'))
    
    def validate(self):
        """Validate all required configuration"""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        
        return True
