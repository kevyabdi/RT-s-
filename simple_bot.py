#!/usr/bin/env python3
"""
Simple SVG to TGS Telegram Bot - No Database Version
Converts SVG files to TGS sticker format with batch processing
"""

import asyncio
import logging
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
import xml.etree.ElementTree as ET
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleConfig:
    """Simple configuration without database"""
    
    def __init__(self):
        # Bot credentials - you can set these as environment variables or use defaults
        self.bot_token = os.getenv("BOT_TOKEN", "8435159197:AAEfNaMfesHU2qhLFh8FsPbP3rEewn3BQyg")
        self.api_id = os.getenv("API_ID", "26176218")
        self.owner_id = int(os.getenv("OWNER_ID", "1096693642"))
        
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
        
        # In-memory storage for admin users (since no database)
        self.admin_users = set()
        self.banned_users = set()
        self.all_users = set()
        
        # Add owner as admin
        if self.owner_id:
            self.admin_users.add(self.owner_id)

class SVGValidator:
    """Validates SVG files for size, dimensions, and format requirements"""
    
    def __init__(self, max_file_size: int = 5 * 1024 * 1024, required_size: Tuple[int, int] = (512, 512)):
        self.max_file_size = max_file_size
        self.required_width, self.required_height = required_size
    
    def validate_file_size(self, file_data: bytes) -> Tuple[bool, str]:
        """Validate file size"""
        if len(file_data) > self.max_file_size:
            size_mb = len(file_data) / (1024 * 1024)
            max_mb = self.max_file_size / (1024 * 1024)
            return False, f"❌ File too large ({size_mb:.1f}MB). Maximum allowed: {max_mb}MB"
        
        return True, "File size OK"
    
    def validate_svg_format(self, file_data: bytes) -> Tuple[bool, str]:
        """Validate that file is a proper SVG"""
        try:
            content = file_data.decode('utf-8', errors='ignore')
            
            if not ('<svg' in content.lower() or '<?xml' in content.lower()):
                return False, "❌ Invalid SVG format"
            
            try:
                root = ET.fromstring(file_data)
                if root.tag.lower().endswith('svg'):
                    return True, "Valid SVG format"
                else:
                    return False, "❌ Not a valid SVG file"
            except ET.ParseError as e:
                return False, f"❌ SVG parsing error: {str(e)}"
                
        except Exception as e:
            logger.error(f"SVG validation error: {e}")
            return False, f"❌ File validation error: {str(e)}"
    
    def validate_file(self, file_data: bytes, filename: str) -> Tuple[bool, str]:
        """Comprehensive file validation"""
        if not filename.lower().endswith('.svg'):
            return False, "❌ Only SVG files are accepted"
        
        size_valid, size_msg = self.validate_file_size(file_data)
        if not size_valid:
            return False, size_msg
        
        format_valid, format_msg = self.validate_svg_format(file_data)
        if not format_valid:
            return False, format_msg
        
        return True, "✅ Valid SVG file"

class SVGToTGSConverter:
    """Handles SVG to TGS conversion using lottie library"""
    
    def __init__(self, output_width: int = 512, output_height: int = 512, fps: int = 60):
        self.output_width = output_width
        self.output_height = output_height
        self.fps = fps
    
    async def convert_svg_to_tgs(self, svg_data: bytes, filename: str) -> Optional[bytes]:
        """Convert SVG data to TGS format"""
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp()
            svg_path = os.path.join(temp_dir, f"input_{filename}")
            tgs_path = os.path.join(temp_dir, f"output_{filename.replace('.svg', '.tgs')}")
            
            with open(svg_path, 'wb') as f:
                f.write(svg_data)
            
            success = await self._run_lottie_convert(svg_path, tgs_path)
            
            if success and os.path.exists(tgs_path):
                with open(tgs_path, 'rb') as f:
                    tgs_data = f.read()
                
                logger.info(f"Successfully converted {filename} to TGS ({len(tgs_data)} bytes)")
                return tgs_data
            else:
                logger.error(f"Conversion failed for {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting {filename}: {e}")
            return None
        
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
    
    async def _run_lottie_convert(self, svg_path: str, tgs_path: str) -> bool:
        """Convert SVG to TGS using lottie_convert.py command line tool"""
        try:
            # Find lottie_convert.py
            lottie_convert_path = "/home/runner/workspace/.pythonlibs/bin/lottie_convert.py"
            
            # Prepare conversion command
            cmd = [
                'python', lottie_convert_path,
                svg_path,
                tgs_path,
                '--sanitize',  # Apply Telegram sticker requirements
                '--optimize', '0',  # No optimization for fastest speed
                '--fps', '30',  # Lower FPS for faster processing
                '--width', '512',  # Force width to 512
                '--height', '512'  # Force height to 512
            ]
            
            logger.info(f"Running conversion command: {' '.join(cmd)}")
            
            # Run conversion in subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Check if conversion was successful
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                logger.error(f"Conversion failed with return code {process.returncode}: {error_msg}")
                return False
            
            # Check if output file exists and has content
            if not os.path.exists(tgs_path) or os.path.getsize(tgs_path) == 0:
                logger.error("Conversion completed but no TGS file was generated")
                return False
            
            # Validate TGS file size (should be under 64KB for Telegram)
            file_size = os.path.getsize(tgs_path)
            if file_size > 64 * 1024:  # 64KB limit
                logger.warning(f"Generated TGS file is {file_size} bytes, which exceeds Telegram's 64KB limit")
            
            logger.info(f"Successfully converted SVG to TGS. Output file: {tgs_path} ({file_size} bytes)")
            return True
                
        except Exception as e:
            logger.error(f"Failed to convert with lottie: {e}")
            return False
    
    def get_tgs_filename(self, svg_filename: str) -> str:
        """Generate TGS filename from SVG filename"""
        base_name = Path(svg_filename).stem
        return f"{base_name}.tgs"

class SimpleSVGToTGSBot:
    """Simple SVG to TGS Bot without database dependencies"""
    
    def __init__(self):
        self.config = SimpleConfig()
        self.validator = SVGValidator(self.config.max_file_size, self.config.required_svg_size)
        self.converter = SVGToTGSConverter(
            self.config.output_width,
            self.config.output_height,
            self.config.output_fps
        )
        
        # In-memory batch processing
        self.user_batches: Dict[int, List] = {}
        self.processing_tasks: Dict[int, asyncio.Task] = {}
    
    def setup_handlers(self, application):
        """Setup all command and message handlers"""
        
        # Start command
        application.add_handler(CommandHandler("start", self.start_command))
        
        # Admin commands
        application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        application.add_handler(CommandHandler("ban", self.ban_command))
        application.add_handler(CommandHandler("unban", self.unban_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("makeadmin", self.make_admin_command))
        application.add_handler(CommandHandler("removeadmin", self.remove_admin_command))
        application.add_handler(CommandHandler("adminhelp", self.admin_help_command))
        
        # Document handler for SVG files
        application.add_handler(MessageHandler(
            filters.Document.FileExtension("svg"), 
            self.handle_svg_document
        ))
        
        # General message handler
        application.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND,
            self.handle_general_message
        ))
        
        # Error handler
        application.add_error_handler(self.error_handler)
        
        logger.info("All handlers registered successfully")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        self.config.all_users.add(user.id)
        
        welcome_text = (
            "🎨 **SVG to TGS Converter Bot**\n\n"
            "Welcome! I can convert your SVG files to TGS format for Telegram stickers.\n\n"
            "📝 **How to use:**\n"
            "• Send me SVG files (one or multiple)\n"
            "• Files will be automatically resized to 512×512 pixels\n"
            "• I'll convert them to TGS format and send them back\n\n"
            "📋 **Requirements:**\n"
            "• SVG format only\n"
            "• Maximum file size: 5MB\n"
            "• Batch processing: up to 15 files at once\n\n"
            "🚀 **Ready to convert your SVG files!**"
        )
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def handle_svg_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle SVG document uploads"""
        user_id = update.effective_user.id
        
        # Check if user is banned
        if user_id in self.config.banned_users:
            await update.message.reply_text("❌ You have been banned from using this bot.")
            return
        
        # Add to users set
        self.config.all_users.add(user_id)
        
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
            
            # Add to batch or start processing
            await self.add_to_batch(
                user_id=user_id,
                file_data=bytes(file_data),
                filename=document.file_name,
                chat_id=update.effective_chat.id,
                context=context
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
    
    async def add_to_batch(self, user_id: int, file_data: bytes, filename: str, chat_id: int, context):
        """Add file to batch processing"""
        if user_id not in self.user_batches:
            self.user_batches[user_id] = []
            
            # Send initial status message
            status_msg = await context.bot.send_message(
                chat_id=chat_id,
                text="⏳ Please wait, processing for 3 seconds..."
            )
            
            # Schedule batch processing
            task = asyncio.create_task(
                self.process_batch_after_delay(user_id, chat_id, context, status_msg.message_id)
            )
            self.processing_tasks[user_id] = task
        
        # Add file to batch
        self.user_batches[user_id].append({
            'data': file_data,
            'filename': filename
        })
        
        # Update status if batch exists
        if len(self.user_batches[user_id]) > 1:
            try:
                task = self.processing_tasks.get(user_id)
                if task and not task.done():
                    # Update the count in the existing status message
                    pass  # The status will be updated in the processing function
            except Exception as e:
                logger.error(f"Error updating batch status: {e}")
    
    async def process_batch_after_delay(self, user_id: int, chat_id: int, context, status_message_id: int):
        """Process batch after delay"""
        try:
            # Wait for processing delay
            await asyncio.sleep(self.config.processing_delay)
            
            batch = self.user_batches.get(user_id, [])
            if not batch:
                return
            
            # Update status
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message_id,
                text=f"🔄 Converting {len(batch)} files..."
            )
            
            successful_conversions = 0
            failed_conversions = 0
            
            # Process each file
            for file_info in batch:
                try:
                    # Validate file
                    is_valid, validation_msg = self.validator.validate_file(
                        file_info['data'], file_info['filename']
                    )
                    
                    if not is_valid:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ {file_info['filename']}\n{validation_msg}"
                        )
                        failed_conversions += 1
                        continue
                    
                    # Convert file
                    tgs_data = await self.converter.convert_svg_to_tgs(
                        file_info['data'], file_info['filename']
                    )
                    
                    if tgs_data:
                        # Send TGS file
                        tgs_filename = self.converter.get_tgs_filename(file_info['filename'])
                        
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=tgs_data,
                            filename=tgs_filename,
                            caption=f"✅ {file_info['filename']} → {tgs_filename}"
                        )
                        
                        successful_conversions += 1
                    else:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ {file_info['filename']}\nConversion failed"
                        )
                        failed_conversions += 1
                    
                    # Small delay between files
                    await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_info['filename']}: {e}")
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ {file_info['filename']}\nProcessing error: {str(e)}"
                    )
                    failed_conversions += 1
            
            # Update final status
            if successful_conversions > 0:
                status_text = "Done ✅"
                if failed_conversions > 0:
                    status_text += f"\n✅ {successful_conversions} converted | ❌ {failed_conversions} failed"
            else:
                status_text = "❌ No files could be converted"
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message_id,
                text=status_text
            )
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message_id,
                    text="❌ Batch processing failed"
                )
            except Exception:
                pass
        
        finally:
            # Cleanup
            if user_id in self.user_batches:
                del self.user_batches[user_id]
            if user_id in self.processing_tasks:
                del self.processing_tasks[user_id]
    
    # Admin Commands
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - Admin only"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.admin_users:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "📢 Usage: /broadcast <message>\n\n"
                "This command will send a message to all bot users."
            )
            return
        
        message_text = " ".join(context.args)
        user_ids = list(self.config.all_users - self.config.banned_users)
        
        if not user_ids:
            await update.message.reply_text("❌ No users found to broadcast to.")
            return
        
        confirmation_msg = await update.message.reply_text(
            f"📢 Starting broadcast to {len(user_ids)} users..."
        )
        
        sent_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                await context.bot.send_message(chat_id=user_id, text=message_text)
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=confirmation_msg.message_id,
            text=f"📢 Broadcast completed!\n"
                 f"✅ Sent: {sent_count}\n"
                 f"❌ Failed: {failed_count}\n"
                 f"📊 Total users: {len(user_ids)}"
        )
    
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command - Admin only"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.admin_users:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /ban <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            if target_user_id == self.config.owner_id:
                await update.message.reply_text("❌ Cannot ban the bot owner.")
                return
            
            if target_user_id == user_id:
                await update.message.reply_text("❌ You cannot ban yourself.")
                return
            
            self.config.banned_users.add(target_user_id)
            await update.message.reply_text(f"✅ User {target_user_id} has been banned.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            await update.message.reply_text("❌ An error occurred while banning the user.")
    
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command - Admin only"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.admin_users:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /unban <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            self.config.banned_users.discard(target_user_id)
            await update.message.reply_text(f"✅ User {target_user_id} has been unbanned.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in unban command: {e}")
            await update.message.reply_text("❌ An error occurred while unbanning the user.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - Admin only"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.admin_users:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        total_users = len(self.config.all_users)
        banned_users = len(self.config.banned_users)
        active_users = total_users - banned_users
        
        stats_text = f"📊 **Bot Statistics**\n\n" \
                    f"👥 Total Users: {total_users}\n" \
                    f"🚫 Banned Users: {banned_users}\n" \
                    f"✅ Active Users: {active_users}\n" \
                    f"🤖 Bot Status: Running"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def make_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /makeadmin command - Owner only"""
        user_id = update.effective_user.id
        
        if user_id != self.config.owner_id:
            await update.message.reply_text("❌ Only the bot owner can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /makeadmin <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            self.config.admin_users.add(target_user_id)
            await update.message.reply_text(f"✅ User {target_user_id} is now an admin.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in makeadmin command: {e}")
            await update.message.reply_text("❌ An error occurred while making the user an admin.")
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removeadmin command - Owner only"""
        user_id = update.effective_user.id
        
        if user_id != self.config.owner_id:
            await update.message.reply_text("❌ Only the bot owner can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /removeadmin <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            if target_user_id == self.config.owner_id:
                await update.message.reply_text("❌ Cannot remove admin privileges from the owner.")
                return
            
            self.config.admin_users.discard(target_user_id)
            await update.message.reply_text(f"✅ Admin privileges removed from user {target_user_id}.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in removeadmin command: {e}")
            await update.message.reply_text("❌ An error occurred while removing admin privileges.")
    
    async def admin_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /adminhelp command - Admin only"""
        user_id = update.effective_user.id
        
        if user_id not in self.config.admin_users:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        is_owner = user_id == self.config.owner_id
        
        help_text = "🛠 **Admin Commands**\n\n"
        help_text += "📢 `/broadcast <message>` - Send message to all users\n"
        help_text += "🚫 `/ban <user_id>` - Ban a user\n"
        help_text += "✅ `/unban <user_id>` - Unban a user\n"
        help_text += "📊 `/stats` - View bot statistics\n"
        help_text += "❓ `/adminhelp` - Show this help\n"
        
        if is_owner:
            help_text += "\n🔧 **Owner Commands**\n"
            help_text += "👑 `/makeadmin <user_id>` - Grant admin privileges\n"
            help_text += "👤 `/removeadmin <user_id>` - Remove admin privileges\n"
        
        help_text += "\n💡 **Tips:**\n"
        help_text += "• Use `/stats` to monitor bot usage and user activity\n"
        help_text += "• Banned users cannot use the bot until unbanned"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_general_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages and non-SVG files"""
        user_id = update.effective_user.id
        
        if user_id in self.config.banned_users:
            return  # Silent ignore for banned users
        
        self.config.all_users.add(user_id)
        message = update.message
        
        if message.document:
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
            await message.reply_text(
                "👋 Hi! Send me SVG files and I'll convert them to TGS format.\n\n"
                "📝 Supported: SVG files only\n"
                "🎯 Output: TGS stickers for Telegram\n"
                "⚡ Batch processing: Send multiple files at once!\n\n"
                "Type /start for more information."
            )
            return
        
        else:
            await message.reply_text(
                "🤔 I'm not sure what to do with that.\n\n"
                "Send me SVG files for conversion to TGS format.\n"
                "Type /start for help."
            )
    
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
    
    def run(self):
        """Start the bot"""
        try:
            # Create application
            application = Application.builder().token(self.config.bot_token).build()
            
            # Setup handlers
            self.setup_handlers(application)
            
            # Start bot
            logger.info("Starting Simple SVG to TGS Telegram Bot...")
            
            # Use polling for all environments (simpler and more reliable)
            logger.info("Bot is ready and polling for messages...")
            application.run_polling(allowed_updates=["message", "callback_query"])
                
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)

if __name__ == "__main__":
    bot = SimpleSVGToTGSBot()
    bot.run()