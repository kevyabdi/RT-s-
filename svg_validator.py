"""
SVG File Validator Module
Validates SVG files for size, dimensions, and format requirements
"""

import xml.etree.ElementTree as ET
import re
import logging
from typing import Tuple, Optional
from io import BytesIO

logger = logging.getLogger(__name__)

class SVGValidator:
    """Validates SVG files according to bot requirements"""
    
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
            # Check if file starts with SVG content
            content = file_data.decode('utf-8', errors='ignore')
            
            # Look for SVG tags
            if not ('<svg' in content.lower() or '<?xml' in content.lower()):
                return False, "❌ Invalid SVG format"
            
            # Try to parse as XML
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
    
    def extract_svg_dimensions(self, file_data: bytes) -> Tuple[Optional[int], Optional[int]]:
        """Extract width and height from SVG file"""
        try:
            root = ET.fromstring(file_data)
            
            # Get width and height attributes
            width_attr = root.get('width', '')
            height_attr = root.get('height', '')
            
            # Parse dimensions
            width = self._parse_dimension(width_attr)
            height = self._parse_dimension(height_attr)
            
            # If no explicit dimensions, try viewBox
            if width is None or height is None:
                viewbox = root.get('viewBox', '')
                if viewbox:
                    try:
                        parts = viewbox.split()
                        if len(parts) >= 4:
                            width = float(parts[2])
                            height = float(parts[3])
                    except (ValueError, IndexError):
                        pass
            
            return width, height
            
        except Exception as e:
            logger.error(f"Error extracting SVG dimensions: {e}")
            return None, None
    
    def _parse_dimension(self, dimension_str: str) -> Optional[float]:
        """Parse dimension string (e.g., '512px', '100%', '50') to numeric value"""
        if not dimension_str:
            return None
        
        # Remove common units and convert to float
        dimension_str = re.sub(r'(px|pt|pc|mm|cm|in|%)', '', dimension_str.strip())
        
        try:
            return float(dimension_str)
        except ValueError:
            return None
    
    def validate_svg_dimensions(self, file_data: bytes) -> Tuple[bool, str]:
        """Validate SVG dimensions"""
        width, height = self.extract_svg_dimensions(file_data)
        
        if width is None or height is None:
            # If we can't determine dimensions, we'll allow it and let the converter handle resizing
            return True, "⚠️ Could not determine dimensions, will resize during conversion"
        
        # Check if dimensions match requirements
        if abs(width - self.required_width) > 1 or abs(height - self.required_height) > 1:
            return True, f"⚠️ Dimensions {int(width)}×{int(height)} will be resized to {self.required_width}×{self.required_height}"
        
        return True, f"✅ Dimensions OK ({int(width)}×{int(height)})"
    
    def validate_file(self, file_data: bytes, filename: str) -> Tuple[bool, str]:
        """
        Comprehensive file validation
        Returns (is_valid, message)
        """
        # Check file extension
        if not filename.lower().endswith('.svg'):
            return False, "❌ Only SVG files are accepted"
        
        # Validate file size
        size_valid, size_msg = self.validate_file_size(file_data)
        if not size_valid:
            return False, size_msg
        
        # Validate SVG format
        format_valid, format_msg = self.validate_svg_format(file_data)
        if not format_valid:
            return False, format_msg
        
        # Validate dimensions (non-blocking)
        dim_valid, dim_msg = self.validate_svg_dimensions(file_data)
        
        # Combine messages
        messages = [format_msg]
        if dim_msg.startswith('⚠️') or dim_msg.startswith('✅'):
            messages.append(dim_msg)
        
        return True, " | ".join(messages)
    
    def get_file_info(self, file_data: bytes, filename: str) -> str:
        """Get detailed file information"""
        size_kb = len(file_data) / 1024
        width, height = self.extract_svg_dimensions(file_data)
        
        info_parts = [
            f"📁 File: {filename}",
            f"📏 Size: {size_kb:.1f} KB"
        ]
        
        if width and height:
            info_parts.append(f"📐 Dimensions: {int(width)}×{int(height)}")
        
        return "\n".join(info_parts)
