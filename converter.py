"""
SVG to TGS Converter Module
Uses python-lottie library to convert SVG files to TGS format
"""

import os
import tempfile
import logging
from typing import Optional, Tuple
import asyncio
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class SVGToTGSConverter:
    """Handles SVG to TGS conversion using python-lottie"""
    
    def __init__(self, output_width: int = 512, output_height: int = 512, fps: int = 60):
        self.output_width = output_width
        self.output_height = output_height
        self.fps = fps
    
    async def convert_svg_to_tgs(self, svg_data: bytes, filename: str) -> Optional[bytes]:
        """
        Convert SVG data to TGS format
        Returns TGS file bytes or None if conversion fails
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            svg_path = os.path.join(temp_dir, f"input_{filename}")
            tgs_path = os.path.join(temp_dir, f"output_{filename.replace('.svg', '.tgs')}")
            
            # Write SVG data to temporary file
            with open(svg_path, 'wb') as f:
                f.write(svg_data)
            
            # Convert using lottie_convert.py
            success = await self._run_lottie_convert(svg_path, tgs_path)
            
            if success and os.path.exists(tgs_path):
                # Read TGS file
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
            # Cleanup temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory: {e}")
    
    async def _run_lottie_convert(self, svg_path: str, tgs_path: str) -> bool:
        """Run lottie_convert.py command asynchronously"""
        try:
            cmd = [
                'python', '-m', 'lottie.converters.lottie_convert',
                svg_path,
                tgs_path,
                '--sanitize',  # Telegram-specific optimization
                '--width', str(self.output_width),
                '--height', str(self.output_height),
                '--fps', str(self.fps)
            ]
            
            # Run conversion process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.debug(f"Lottie conversion successful: {stdout.decode()}")
                return True
            else:
                logger.error(f"Lottie conversion failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to run lottie_convert: {e}")
            return False
    
    async def validate_and_convert(self, svg_data: bytes, filename: str) -> Tuple[bool, Optional[bytes], str]:
        """
        Validate SVG and convert to TGS
        Returns (success, tgs_data, message)
        """
        try:
            # Basic validation
            if len(svg_data) == 0:
                return False, None, "❌ Empty file received"
            
            if len(svg_data) > 10 * 1024 * 1024:  # 10MB limit
                return False, None, "❌ File too large (max 10MB)"
            
            # Convert to TGS
            tgs_data = await self.convert_svg_to_tgs(svg_data, filename)
            
            if tgs_data:
                return True, tgs_data, "✅ Conversion successful"
            else:
                return False, None, "❌ Conversion failed"
                
        except Exception as e:
            logger.error(f"Validation/conversion error for {filename}: {e}")
            return False, None, f"❌ Error: {str(e)}"
    
    def get_tgs_filename(self, svg_filename: str) -> str:
        """Generate TGS filename from SVG filename"""
        base_name = Path(svg_filename).stem
        return f"{base_name}.tgs"
