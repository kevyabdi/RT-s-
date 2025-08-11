"""
User Handlers Module
Handles all user interactions and file processing
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from batch_processor import BatchProcessor

logger = logging.getLogger(__name__)

class UserHandlers:
    """Handles user interactions and file processing"""
    
    def __init__(self, database, config):
        self.database = database
        self.config = config
        self.batch_processor = None  # Will be set later with bot instance
    
    def set_batch_processor(self, bot):
        """Set the batch processor with bot instance"""
        self.batch_processor = BatchProcessor(self.config, self.database, bot)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Add user to database
        await self.database.add_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        welcome_text = (
            "🎨 **SVG to TGS Converter Bot**\n\n"
            "Welcome! I can convert your SVG files to TGS format for Telegram stickers.\n\n"
            "📝 **How to use:**\n"
            "• Send me SVG files (one or multiple)\n"
            "• Files will be automatically resized to 512×512 pixels\n"
            "• I'll convert them to TGS format and send them back\n\n"
            "📋 **Requirements:**\n"
            "• SVG format only\n"
            "• Maximum file size: 10MB\n"
            "• Batch processing: up to 15 files at once\n\n"
            "🚀 **Ready to convert your SVG files!**"
        )
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def handle_svg_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle SVG document uploads"""
        user_id = update.effective_user.id
        
        # Check if user is banned
        if await self.database.is_user_banned(user_id):
            await update.message.reply_text("❌ You have been banned from using this bot.")
            return
        
        # Update user info
        user = update.effective_user
        await self.database.add_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        # Get document
        document = update.message.document
        
        if not document:
            await update.message.reply_text("❌ No document received.")
            return
        
        # Check file extension
        if not document.file_name.lower().endswith('.svg'):
            await update.message.reply_text(
                "❌ Only SVG files are accepted.\n"
                "Please send a valid SVG file."
            )
            return
        
        # Check file size
        if document.file_size > self.config.max_file_size:
            size_mb = document.file_size / (1024 * 1024)
            max_mb = self.config.max_file_size / (1024 * 1024)
            await update.message.reply_text(
                f"❌ File too large ({size_mb:.1f}MB).\n"
                f"Maximum allowed: {max_mb}MB"
            )
            return
        
        try:
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_data = await file.download_as_bytearray()
            
            # Add to batch processor
            success = await self.batch_processor.add_file_to_batch(
                user_id=user_id,
                file_data=bytes(file_data),
                filename=document.file_name,
                message_id=update.message.message_id,
                chat_id=update.effective_chat.id
            )
            
            if not success:
                await update.message.reply_text(
                    "❌ Failed to add file to processing queue. Please try again."
                )
            
        except TelegramError as e:
            logger.error(f"Telegram error downloading file: {e}")
            await update.message.reply_text(
                "❌ Failed to download file. Please try again."
            )
        except Exception as e:
            logger.error(f"Error handling SVG document: {e}")
            await update.message.reply_text(
                "❌ An error occurred while processing your file. Please try again."
            )
    
    async def handle_general_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages and non-SVG files"""
        user_id = update.effective_user.id
        
        # Check if user is banned
        if await self.database.is_user_banned(user_id):
            return  # Silent ignore for banned users
        
        # Update user info
        user = update.effective_user
        await self.database.add_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        message = update.message
        
        # Handle different message types
        if message.document:
            # Non-SVG document
            file_name = message.document.file_name or "unknown"
            
            if not file_name.lower().endswith('.svg'):
                await message.reply_text(
                    "❌ Only SVG files are supported.\n\n"
                    "Please send a valid SVG file for conversion to TGS format.\n"
                    "You can create SVG files using tools like:\n"
                    "• Inkscape (free)\n"
                    "• Adobe Illustrator\n"
                    "• Figma\n"
                    "• Canva"
                )
                return
        
        elif message.photo:
            await message.reply_text(
                "📷 I can only convert SVG files, not images.\n\n"
                "To convert your image to SVG:\n"
                "1. Use an online converter like convertio.co\n"
                "2. Or recreate it as an SVG in a vector graphics editor\n"
                "3. Then send me the SVG file!"
            )
            return
        
        elif message.text and not message.text.startswith('/'):
            # Regular text message
            batch_status = self.batch_processor.get_user_batch_status(user_id)
            
            if batch_status:
                await message.reply_text(
                    f"🔄 I'm currently processing your files.\n"
                    f"Status: {batch_status}\n\n"
                    f"Please wait for the conversion to complete."
                )
            else:
                await message.reply_text(
                    "👋 Hi! Send me SVG files and I'll convert them to TGS format.\n\n"
                    "📝 Supported: SVG files only\n"
                    "🎯 Output: TGS stickers for Telegram\n"
                    "⚡ Batch processing: Send multiple files at once!\n\n"
                    "Type /start for more information."
                )
            return
        
        elif message.video or message.animation:
            await message.reply_text(
                "🎥 I only work with SVG files.\n\n"
                "For animated stickers, you need to:\n"
                "1. Create or convert your animation to SVG format\n"
                "2. Send me the SVG file\n"
                "3. I'll convert it to TGS format for Telegram"
            )
            return
        
        elif message.sticker:
            await message.reply_text(
                "🔄 I convert SVG files TO stickers, not the other way around.\n\n"
                "Send me an SVG file and I'll create a TGS sticker from it!"
            )
            return
        
        else:
            # Unknown message type
            await message.reply_text(
                "🤔 I'm not sure what to do with that.\n\n"
                "Send me SVG files for conversion to TGS format.\n"
                "Type /start for help."
            )
