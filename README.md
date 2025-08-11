# SVG to TGS Telegram Bot

A fast and efficient Telegram bot that converts SVG files to TGS (Telegram Sticker) format with batch processing capabilities and comprehensive admin controls.

## Features

- **Fast SVG to TGS Conversion**: Converts SVG files to TGS format optimized for Telegram stickers
- **Batch Processing**: Handle up to 15 SVG files simultaneously
- **Smart User Experience**: Shows "Please wait for 3 seconds..." then "Done ✅"
- **File Validation**: Only accepts SVG files up to 5MB
- **Automatic Resizing**: Converts all files to 512×512 pixels (Telegram sticker standard)
- **Admin System**: Complete user management with broadcast, ban/unban features
- **No Database Required**: Lightweight in-memory storage
- **Ready for Deployment**: Configured for Render, Heroku, and other platforms

## Quick Start

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd svg-to-tgs-bot
```

### 2. Install Dependencies
```bash
pip install python-telegram-bot lottie python-dotenv asyncpg cairosvg
```

Or if you have a requirements file:
```bash
pip install -r deps.txt
```

### 3. Configure Environment (Optional)
The bot comes with pre-configured credentials, but you can override them with environment variables:

```bash
export BOT_TOKEN="your_bot_token_here"
export OWNER_ID="your_telegram_user_id"
export API_ID="your_api_id"
```

**Default Configuration:**
- BOT_TOKEN: Pre-configured
- OWNER_ID: Pre-configured (1096693642)
- API_ID: Pre-configured (26176218)

### 4. Run the Bot
```bash
python simple_bot.py
```

## Deployment

### Deploy to Render

1. **Create a New Web Service** on [Render](https://render.com)
2. **Connect your GitHub repository**
3. **Configure the service:**
   - **Build Command**: `pip install python-telegram-bot lottie python-dotenv asyncpg cairosvg`
   - **Start Command**: `python simple_bot.py`
   - **Environment Variables** (optional - bot has pre-configured defaults):
     ```
     BOT_TOKEN=your_bot_token
     OWNER_ID=your_telegram_user_id
     API_ID=your_api_id
     ```

### Deploy to Heroku

1. **Create a new Heroku app**
2. **Update Procfile** for Heroku (change to `web: python simple_bot.py`)
3. **Deploy using Git:**
   ```bash
   git add .
   git commit -m "Deploy SVG to TGS bot"
   git push heroku main
   ```
4. **Set environment variables** (optional - bot has defaults):
   ```bash
   heroku config:set BOT_TOKEN=your_bot_token
   heroku config:set OWNER_ID=your_telegram_user_id
   heroku config:set API_ID=your_api_id
   ```

## How to Use

### For Users
1. Start a conversation with your bot on Telegram
2. Send `/start` to see the welcome message
3. Send one or more SVG files
4. Wait for conversion (bot shows progress)
5. Receive TGS files ready for use as Telegram stickers

### Admin Commands
- `/broadcast <message>` - Send message to all users
- `/ban <user_id>` - Ban a user from using the bot
- `/unban <user_id>` - Unban a previously banned user
- `/stats` - View bot usage statistics
- `/adminhelp` - Show all admin commands

### Owner-Only Commands
- `/makeadmin <user_id>` - Grant admin privileges to a user
- `/removeadmin <user_id>` - Remove admin privileges from a user

## File Requirements

- **Format**: SVG files only
- **Size**: Maximum 5MB per file
- **Output**: TGS format (512×512 pixels)
- **Batch Limit**: Up to 15 files at once

## Bot Behavior

When users send SVG files:

1. **Immediate Response**: "Please wait, processing for 3 seconds..."
2. **Processing**: Files are validated and converted
3. **Completion**: Message updates to "Done ✅"
4. **Delivery**: TGS files sent one by one without extra messages

## Technical Details

### Architecture
- **No Database**: All data stored in memory (users, admins, banned list)
- **Async Processing**: Non-blocking file conversion using asyncio
- **Error Handling**: Comprehensive error messages and logging
- **Rate Limiting**: Built-in delays to respect Telegram API limits

### Dependencies
- `python-telegram-bot` - Telegram Bot API
- `lottie` - SVG to TGS conversion
- `python-dotenv` - Environment variable management
- `asyncpg` - Database support (not used in simple version)

### File Structure
```
├── simple_bot.py          # Main bot application (no database)
├── bot.py                 # Full bot with database (alternative)
├── config.py              # Configuration management
├── converter.py           # SVG to TGS conversion logic
├── database.py            # Database operations (not used in simple version)
├── svg_validator.py       # File validation
├── batch_processor.py     # Batch processing logic
├── admin_commands.py      # Admin command handlers
├── user_handlers.py       # User interaction handlers
├── Procfile               # Deployment configuration
├── runtime.txt            # Python version specification
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Error Handling

The bot handles various error scenarios:

- **Invalid file types**: Clear message directing users to send SVG files
- **File too large**: Size limit notification with current file size
- **Conversion failures**: Specific error messages for each file
- **Network issues**: Retry mechanisms and user notifications
- **Rate limiting**: Automatic delays and queue management

## Customization

### Modify File Limits
Edit `simple_bot.py`:
```python
self.max_file_size = 10 * 1024 * 1024  # Change to 10MB
self.max_batch_size = 20  # Allow 20 files at once
```

### Change Output Settings
```python
self.output_width = 1024   # Change output dimensions
self.output_height = 1024
self.fps = 30              # Change frame rate
```

### Modify Processing Delay
```python
self.processing_delay = 5  # Wait 5 seconds instead of 3
```

## Troubleshooting

### Bot Not Responding
1. Check if bot token is valid
2. Verify bot is not banned by Telegram
3. Check server logs for errors

### Conversion Failures
1. Ensure SVG files are valid
2. Check file size limits
3. Verify lottie library installation

### Admin Commands Not Working
1. Confirm OWNER_ID is set correctly
2. Check user ID format (numeric only)
3. Verify admin privileges

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues or questions:

1. Check the bot logs for error messages
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed
4. Test with valid SVG files

## Changelog

### Version 1.0.0
- Initial release
- SVG to TGS conversion
- Batch processing
- Admin system
- No database dependency
- Ready for deployment