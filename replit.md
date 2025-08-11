# Overview

SVG to TGS Converter Telegram Bot is a specialized bot that converts SVG (Scalable Vector Graphics) files to TGS (Telegram Sticker) format. The bot supports batch processing of multiple files, has administrative features for broadcasting messages, and includes comprehensive validation and error handling. It's designed to help users create Telegram stickers from SVG files with automatic resizing to the required 512×512 pixel format.

## Recent Changes (August 2025)
- **Fixed SVG to TGS Conversion**: Now using subprocess approach with lottie_convert.py command-line tool
- **Working Conversion Pipeline**: Successfully converting SVG files to TGS format using --sanitize flag
- **Simplified Architecture**: Removed database dependency for easier deployment
- **Embedded Credentials**: Bot now includes pre-configured credentials for immediate use
- **GitHub Ready**: Complete repository setup with README, LICENSE, and deployment files
- **Working Status**: Bot is currently running and responding to messages with functional conversion
- **Memory-Based Storage**: User data, admin lists, and banned users stored in memory (resets on restart)

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework & Structure
The application uses the python-telegram-bot library for Telegram integration and follows a modular architecture with clear separation of concerns. The main bot class (`SVGToTGSBot`) orchestrates all functionality through specialized modules for user handling, admin commands, file conversion, and database operations.

## Database Layer
Uses PostgreSQL with asyncpg for connection pooling and asynchronous operations. The database stores user information, admin privileges, conversion statistics, and ban status. Connection pooling is configured with 1-10 connections and 60-second command timeouts for reliability.

## File Processing Pipeline
- **SVG Validation**: Validates file size (5MB limit), format integrity, and SVG structure using XML parsing
- **Batch Processing**: Supports up to 15 files per batch with timeout handling and status tracking
- **Conversion Engine**: Uses python-lottie library to convert SVG files to TGS format with configurable output dimensions (512×512) and frame rate (60fps)
- **Temporary File Management**: Uses system temporary directories for processing with automatic cleanup

## Administrative System
Implements role-based access control with owner and admin privileges. Admins can broadcast messages to all users and manage bot operations. The system includes permission checking and command validation.

## Error Handling & Logging
Comprehensive logging system tracks all operations, errors, and user interactions. Error handling includes graceful fallbacks for file processing failures, network issues, and database connectivity problems.

## Configuration Management
Environment-based configuration system using dotenv for local development and environment variables for production deployment. Supports both development and production environments with appropriate settings.

# External Dependencies

## Core Libraries
- **python-telegram-bot**: Telegram Bot API integration and webhook handling
- **asyncpg**: PostgreSQL async database driver with connection pooling
- **python-lottie**: SVG to TGS conversion library for Telegram sticker format

## Database
- **PostgreSQL**: Primary database for user management, statistics, and administrative data

## Development Tools
- **python-dotenv**: Environment variable management for local development
- **logging**: Built-in Python logging for application monitoring and debugging

## System Dependencies
- **tempfile**: System temporary directory management for file processing
- **subprocess**: External command execution for conversion operations
- **xml.etree.ElementTree**: XML parsing for SVG validation

## Runtime Environment
- **Python 3.11.9**: Specified runtime version for consistent deployment
- Compatible with cloud platforms like Render and Heroku through environment detection