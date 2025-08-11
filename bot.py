#!/usr/bin/env python3
"""
SVG to TGS Telegram Bot - Main Entry Point
Converts SVG files to TGS sticker format with batch processing and admin features
"""

import asyncio
import logging
import os
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import Config
from database import Database
from user_handlers import UserHandlers
from admin_commands import AdminCommands

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SVGToTGSBot:
    """Main bot class that orchestrates all functionality"""
    
    def __init__(self):
        self.config = Config()
        self.database = Database(self.config.database_url)
        self.user_handlers = UserHandlers(self.database, self.config)
        self.admin_commands = AdminCommands(self.database, self.config)
        
    async def setup_database(self):
        """Initialize database tables"""
        try:
            await self.database.initialize()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            sys.exit(1)
    
    def setup_handlers(self, application):
        """Setup all command and message handlers"""
        
        # Start command
        application.add_handler(CommandHandler("start", self.user_handlers.start_command))
        
        # Admin commands
        application.add_handler(CommandHandler("broadcast", self.admin_commands.broadcast_command))
        application.add_handler(CommandHandler("ban", self.admin_commands.ban_command))
        application.add_handler(CommandHandler("unban", self.admin_commands.unban_command))
        application.add_handler(CommandHandler("stats", self.admin_commands.stats_command))
        application.add_handler(CommandHandler("makeadmin", self.admin_commands.make_admin_command))
        application.add_handler(CommandHandler("removeadmin", self.admin_commands.remove_admin_command))
        application.add_handler(CommandHandler("adminhelp", self.admin_commands.admin_help_command))
        
        # Document handler for SVG files
        application.add_handler(MessageHandler(
            filters.Document.FileExtension("svg"), 
            self.user_handlers.handle_svg_document
        ))
        
        # General message handler for any other files or messages
        application.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND,
            self.user_handlers.handle_general_message
        ))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("All handlers registered successfully")
    
    async def error_handler(self, update, context):
        """Global error handler"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again later."
                )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")
    
    async def post_init(self, application):
        """Post initialization setup"""
        await self.setup_database()
        
        # Start batch processor
        asyncio.create_task(self.user_handlers.batch_processor.start_processing())
        logger.info("Batch processor started")
    
    def run(self):
        """Start the bot"""
        try:
            # Create application
            application = Application.builder().token(self.config.bot_token).build()
            
            # Setup handlers
            self.setup_handlers(application)
            
            # Run post init
            application.post_init = self.post_init
            
            # Start bot
            logger.info("Starting SVG to TGS Telegram Bot...")
            
            # For hosting platforms like Render, use webhooks
            port = int(os.environ.get('PORT', 8000))
            
            if os.environ.get('RENDER') or os.environ.get('HEROKU_APP_NAME'):
                # Use webhooks for hosting platforms
                webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', os.environ.get('HEROKU_APP_NAME') + '.herokuapp.com')}"
                application.run_webhook(
                    listen="0.0.0.0",
                    port=port,
                    webhook_url=webhook_url
                )
            else:
                # Use polling for local development
                application.run_polling(allowed_updates=["message", "callback_query"])
                
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)

if __name__ == "__main__":
    bot = SVGToTGSBot()
    bot.run()
