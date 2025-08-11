"""
Admin Commands Module
Handles all administrative commands for the bot
"""

import asyncio
import logging
from typing import List
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class AdminCommands:
    """Handles administrative commands"""
    
    def __init__(self, database, config):
        self.database = database
        self.config = config
    
    async def is_owner(self, user_id: int) -> bool:
        """Check if user is the bot owner"""
        return self.config.owner_id and user_id == self.config.owner_id
    
    async def is_admin_or_owner(self, user_id: int) -> bool:
        """Check if user is admin or owner"""
        if await self.is_owner(user_id):
            return True
        return await self.database.is_user_admin(user_id)
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - Admin only"""
        user_id = update.effective_user.id
        
        # Check admin privileges
        if not await self.is_admin_or_owner(user_id):
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        # Check if message is provided
        if not context.args:
            await update.message.reply_text(
                "📢 Usage: /broadcast <message>\n\n"
                "This command will send a message to all bot users.\n"
                "You can also reply to a message with /broadcast to forward it."
            )
            return
        
        # Get broadcast message
        if update.message.reply_to_message:
            # Forwarding a message
            broadcast_message = update.message.reply_to_message
            message_text = "Forwarded message"
        else:
            # Text message
            message_text = " ".join(context.args)
            if len(message_text) > self.config.max_broadcast_length:
                await update.message.reply_text(
                    f"❌ Message too long! Maximum {self.config.max_broadcast_length} characters allowed."
                )
                return
            broadcast_message = message_text
        
        # Get all user IDs
        user_ids = await self.database.get_all_user_ids()
        
        if not user_ids:
            await update.message.reply_text("❌ No users found to broadcast to.")
            return
        
        # Send confirmation
        confirmation_msg = await update.message.reply_text(
            f"📢 Starting broadcast to {len(user_ids)} users...\n"
            f"Message: {message_text[:100]}{'...' if len(message_text) > 100 else ''}"
        )
        
        # Start broadcasting
        sent_count, failed_count = await self._send_broadcast(
            broadcast_message, user_ids, update.effective_chat.id, confirmation_msg.message_id
        )
        
        # Log broadcast
        await self.database.log_broadcast(user_id, message_text, sent_count, failed_count)
        
        # Update confirmation message
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=confirmation_msg.message_id,
            text=f"📢 Broadcast completed!\n"
                 f"✅ Sent: {sent_count}\n"
                 f"❌ Failed: {failed_count}\n"
                 f"📊 Total users: {len(user_ids)}"
        )
    
    async def _send_broadcast(self, message, user_ids: List[int], admin_chat_id: int, status_message_id: int) -> tuple:
        """Send broadcast message to all users"""
        sent_count = 0
        failed_count = 0
        total_users = len(user_ids)
        
        for i, user_id in enumerate(user_ids):
            try:
                if isinstance(message, str):
                    # Text message
                    await asyncio.create_task(
                        self._send_broadcast_message(user_id, message)
                    )
                else:
                    # Forward message
                    await asyncio.create_task(
                        self._forward_broadcast_message(user_id, message)
                    )
                
                sent_count += 1
                
                # Update progress every 10 messages
                if (i + 1) % 10 == 0:
                    try:
                        progress = (i + 1) / total_users * 100
                        await asyncio.create_task(
                            self._update_broadcast_progress(
                                admin_chat_id, status_message_id, 
                                i + 1, total_users, sent_count, failed_count, progress
                            )
                        )
                    except Exception:
                        pass
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
                continue
        
        return sent_count, failed_count
    
    async def _send_broadcast_message(self, user_id: int, message: str):
        """Send text broadcast message to a user"""
        from telegram import Bot
        bot = Bot(token=self.config.bot_token)
        await bot.send_message(chat_id=user_id, text=message)
    
    async def _forward_broadcast_message(self, user_id: int, original_message):
        """Forward broadcast message to a user"""
        from telegram import Bot
        bot = Bot(token=self.config.bot_token)
        
        if original_message.text:
            await bot.send_message(chat_id=user_id, text=original_message.text)
        elif original_message.photo:
            await bot.send_photo(
                chat_id=user_id, 
                photo=original_message.photo[-1].file_id,
                caption=original_message.caption
            )
        elif original_message.document:
            await bot.send_document(
                chat_id=user_id,
                document=original_message.document.file_id,
                caption=original_message.caption
            )
        elif original_message.video:
            await bot.send_video(
                chat_id=user_id,
                video=original_message.video.file_id,
                caption=original_message.caption
            )
    
    async def _update_broadcast_progress(self, chat_id: int, message_id: int, 
                                       current: int, total: int, sent: int, 
                                       failed: int, progress: float):
        """Update broadcast progress"""
        from telegram import Bot
        bot = Bot(token=self.config.bot_token)
        
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"📢 Broadcasting... {progress:.1f}%\n"
                     f"📤 Processed: {current}/{total}\n"
                     f"✅ Sent: {sent}\n"
                     f"❌ Failed: {failed}"
            )
        except Exception as e:
            logger.debug(f"Failed to update broadcast progress: {e}")
    
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ban command - Admin only"""
        user_id = update.effective_user.id
        
        if not await self.is_admin_or_owner(user_id):
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /ban <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            # Prevent banning owner or self
            if target_user_id == self.config.owner_id:
                await update.message.reply_text("❌ Cannot ban the bot owner.")
                return
            
            if target_user_id == user_id:
                await update.message.reply_text("❌ You cannot ban yourself.")
                return
            
            # Ban user
            success = await self.database.ban_user(target_user_id)
            
            if success:
                await update.message.reply_text(f"✅ User {target_user_id} has been banned.")
            else:
                await update.message.reply_text(f"❌ Failed to ban user {target_user_id}.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            await update.message.reply_text("❌ An error occurred while banning the user.")
    
    async def unban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unban command - Admin only"""
        user_id = update.effective_user.id
        
        if not await self.is_admin_or_owner(user_id):
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /unban <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            # Unban user
            success = await self.database.unban_user(target_user_id)
            
            if success:
                await update.message.reply_text(f"✅ User {target_user_id} has been unbanned.")
            else:
                await update.message.reply_text(f"❌ Failed to unban user {target_user_id}.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in unban command: {e}")
            await update.message.reply_text("❌ An error occurred while unbanning the user.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - Admin only"""
        user_id = update.effective_user.id
        
        if not await self.is_admin_or_owner(user_id):
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        try:
            # Get user statistics
            total_users, banned_users, active_users = await self.database.get_user_stats()
            
            stats_text = f"📊 **Bot Statistics**\n\n" \
                        f"👥 Total Users: {total_users}\n" \
                        f"🚫 Banned Users: {banned_users}\n" \
                        f"✅ Active Users (30 days): {active_users}\n" \
                        f"🤖 Bot Status: Running"
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("❌ An error occurred while fetching statistics.")
    
    async def make_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /makeadmin command - Owner only"""
        user_id = update.effective_user.id
        
        if not await self.is_owner(user_id):
            await update.message.reply_text("❌ Only the bot owner can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /makeadmin <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            # Make admin
            success = await self.database.make_admin(target_user_id)
            
            if success:
                await update.message.reply_text(f"✅ User {target_user_id} is now an admin.")
            else:
                await update.message.reply_text(f"❌ Failed to make user {target_user_id} an admin.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in makeadmin command: {e}")
            await update.message.reply_text("❌ An error occurred while making the user an admin.")
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removeadmin command - Owner only"""
        user_id = update.effective_user.id
        
        if not await self.is_owner(user_id):
            await update.message.reply_text("❌ Only the bot owner can use this command.")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /removeadmin <user_id>")
            return
        
        try:
            target_user_id = int(context.args[0])
            
            # Remove admin
            success = await self.database.remove_admin(target_user_id)
            
            if success:
                await update.message.reply_text(f"✅ Admin privileges removed from user {target_user_id}.")
            else:
                await update.message.reply_text(f"❌ Failed to remove admin privileges from user {target_user_id}.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        except Exception as e:
            logger.error(f"Error in removeadmin command: {e}")
            await update.message.reply_text("❌ An error occurred while removing admin privileges.")
    
    async def admin_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /adminhelp command - Admin only"""
        user_id = update.effective_user.id
        
        if not await self.is_admin_or_owner(user_id):
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        
        is_owner = await self.is_owner(user_id)
        
        help_text = "🛠 **Admin Commands**\n\n"
        
        # Admin commands
        help_text += "📢 `/broadcast <message>` - Send message to all users\n"
        help_text += "🚫 `/ban <user_id>` - Ban a user\n"
        help_text += "✅ `/unban <user_id>` - Unban a user\n"
        help_text += "📊 `/stats` - View bot statistics\n"
        help_text += "❓ `/adminhelp` - Show this help\n"
        
        # Owner-only commands
        if is_owner:
            help_text += "\n🔧 **Owner Commands**\n"
            help_text += "👑 `/makeadmin <user_id>` - Grant admin privileges\n"
            help_text += "👤 `/removeadmin <user_id>` - Remove admin privileges\n"
        
        help_text += "\n💡 **Tips:**\n"
        help_text += "• You can reply to any message with `/broadcast` to forward it\n"
        help_text += "• Use `/stats` to monitor bot usage and user activity\n"
        help_text += "• Banned users cannot use the bot until unbanned"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
