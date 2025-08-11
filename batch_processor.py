"""
Batch Processor Module
Handles batch processing of multiple SVG files for conversion
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

from converter import SVGToTGSConverter
from svg_validator import SVGValidator

logger = logging.getLogger(__name__)

@dataclass
class FileData:
    """Represents a file to be processed"""
    file_data: bytes
    filename: str
    message_id: int
    chat_id: int

@dataclass
class BatchJob:
    """Represents a batch processing job"""
    user_id: int
    files: List[FileData]
    status_message_id: int
    chat_id: int
    created_at: datetime
    completed: bool = False

class BatchProcessor:
    """Handles batch processing of SVG files"""
    
    def __init__(self, config, database, bot):
        self.config = config
        self.database = database
        self.bot = bot
        self.converter = SVGToTGSConverter(
            config.output_width,
            config.output_height,
            config.output_fps
        )
        self.validator = SVGValidator(config.max_file_size, config.required_svg_size)
        
        # Active batch jobs
        self.batch_jobs: Dict[int, BatchJob] = {}  # user_id -> BatchJob
        
        # Processing queue
        self.processing_queue = asyncio.Queue()
        self.is_processing = False
    
    async def add_file_to_batch(self, user_id: int, file_data: bytes, filename: str, 
                               message_id: int, chat_id: int) -> bool:
        """Add a file to user's batch processing queue"""
        try:
            # Create file data object
            file_obj = FileData(file_data, filename, message_id, chat_id)
            
            # Get or create batch job for user
            if user_id not in self.batch_jobs:
                # Create new batch job
                batch_job = BatchJob(
                    user_id=user_id,
                    files=[file_obj],
                    status_message_id=message_id,
                    chat_id=chat_id,
                    created_at=datetime.now()
                )
                self.batch_jobs[user_id] = batch_job
                
                # Send initial status message
                try:
                    status_msg = await self.bot.send_message(
                        chat_id=chat_id,
                        text="⏳ Please wait, processing for 3 seconds..."
                    )
                    batch_job.status_message_id = status_msg.message_id
                except Exception as e:
                    logger.error(f"Failed to send status message: {e}")
                
                # Schedule processing after delay
                asyncio.create_task(self._schedule_batch_processing(user_id))
                
            else:
                # Add to existing batch
                batch_job = self.batch_jobs[user_id]
                if len(batch_job.files) < self.config.max_batch_size:
                    batch_job.files.append(file_obj)
                    
                    # Update status message
                    try:
                        await self.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=batch_job.status_message_id,
                            text=f"⏳ Please wait, processing {len(batch_job.files)} files for 3 seconds..."
                        )
                    except Exception as e:
                        logger.error(f"Failed to update status message: {e}")
                else:
                    # Batch is full, process immediately
                    await self.processing_queue.put(user_id)
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding file to batch for user {user_id}: {e}")
            return False
    
    async def _schedule_batch_processing(self, user_id: int):
        """Schedule batch processing after delay"""
        try:
            # Wait for the processing delay
            await asyncio.sleep(self.config.processing_delay)
            
            # Add to processing queue
            await self.processing_queue.put(user_id)
            
        except Exception as e:
            logger.error(f"Error scheduling batch processing for user {user_id}: {e}")
    
    async def start_processing(self):
        """Start the batch processing worker"""
        self.is_processing = True
        
        while self.is_processing:
            try:
                # Wait for batch jobs
                user_id = await self.processing_queue.get()
                
                if user_id in self.batch_jobs:
                    await self._process_batch(user_id)
                
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, user_id: int):
        """Process a batch of files for a user"""
        batch_job = self.batch_jobs.get(user_id)
        if not batch_job or batch_job.completed:
            return
        
        try:
            logger.info(f"Processing batch of {len(batch_job.files)} files for user {user_id}")
            
            # Update status to processing
            try:
                await self.bot.edit_message_text(
                    chat_id=batch_job.chat_id,
                    message_id=batch_job.status_message_id,
                    text=f"🔄 Converting {len(batch_job.files)} files..."
                )
            except Exception as e:
                logger.error(f"Failed to update processing status: {e}")
            
            successful_conversions = 0
            failed_conversions = 0
            
            # Process each file
            for i, file_obj in enumerate(batch_job.files):
                try:
                    # Validate file
                    is_valid, validation_msg = self.validator.validate_file(
                        file_obj.file_data, file_obj.filename
                    )
                    
                    if not is_valid:
                        await self._send_error_message(batch_job.chat_id, file_obj.filename, validation_msg)
                        failed_conversions += 1
                        await self.database.log_conversion(
                            user_id, file_obj.filename, len(file_obj.file_data), 
                            False, validation_msg
                        )
                        continue
                    
                    # Convert file
                    success, tgs_data, convert_msg = await self.converter.validate_and_convert(
                        file_obj.file_data, file_obj.filename
                    )
                    
                    if success and tgs_data:
                        # Send TGS file
                        tgs_filename = self.converter.get_tgs_filename(file_obj.filename)
                        
                        await self.bot.send_document(
                            chat_id=batch_job.chat_id,
                            document=tgs_data,
                            filename=tgs_filename,
                            caption=f"✅ {file_obj.filename} → {tgs_filename}"
                        )
                        
                        successful_conversions += 1
                        await self.database.log_conversion(
                            user_id, file_obj.filename, len(file_obj.file_data), True
                        )
                    else:
                        await self._send_error_message(batch_job.chat_id, file_obj.filename, convert_msg)
                        failed_conversions += 1
                        await self.database.log_conversion(
                            user_id, file_obj.filename, len(file_obj.file_data), 
                            False, convert_msg
                        )
                    
                    # Small delay between files
                    if i < len(batch_job.files) - 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error processing file {file_obj.filename}: {e}")
                    await self._send_error_message(
                        batch_job.chat_id, file_obj.filename, f"❌ Processing error: {str(e)}"
                    )
                    failed_conversions += 1
            
            # Update final status
            try:
                if successful_conversions > 0:
                    status_text = f"Done ✅"
                    if failed_conversions > 0:
                        status_text += f"\n✅ {successful_conversions} converted | ❌ {failed_conversions} failed"
                else:
                    status_text = "❌ No files could be converted"
                
                await self.bot.edit_message_text(
                    chat_id=batch_job.chat_id,
                    message_id=batch_job.status_message_id,
                    text=status_text
                )
            except Exception as e:
                logger.error(f"Failed to update final status: {e}")
            
            # Mark batch as completed
            batch_job.completed = True
            
            # Clean up after some time
            asyncio.create_task(self._cleanup_batch(user_id, delay=300))  # 5 minutes
            
        except Exception as e:
            logger.error(f"Error processing batch for user {user_id}: {e}")
            
            # Send error message
            try:
                await self.bot.edit_message_text(
                    chat_id=batch_job.chat_id,
                    message_id=batch_job.status_message_id,
                    text="❌ Batch processing failed"
                )
            except Exception:
                pass
    
    async def _send_error_message(self, chat_id: int, filename: str, error_msg: str):
        """Send error message for a failed file"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ {filename}\n{error_msg}"
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
    
    async def _cleanup_batch(self, user_id: int, delay: int = 300):
        """Clean up completed batch job after delay"""
        try:
            await asyncio.sleep(delay)
            if user_id in self.batch_jobs:
                del self.batch_jobs[user_id]
                logger.debug(f"Cleaned up batch job for user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up batch for user {user_id}: {e}")
    
    def stop_processing(self):
        """Stop the batch processor"""
        self.is_processing = False
    
    def get_user_batch_status(self, user_id: int) -> Optional[str]:
        """Get current batch status for user"""
        batch_job = self.batch_jobs.get(user_id)
        if not batch_job:
            return None
        
        if batch_job.completed:
            return "Completed"
        
        elapsed = datetime.now() - batch_job.created_at
        return f"Processing {len(batch_job.files)} files (elapsed: {elapsed.seconds}s)"
