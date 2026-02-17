# Bible Notice Telegram Bot

A Telegram bot that automatically sends daily Bible reading passages and QT texts.

## Features
- **Multi-language**: Korean (KRV), English (ESV), Mongolian (MUV).
- **Automated**: Runs via GitHub Actions.
- **AI-Powered**: Uses Gemini 2.0 Flash to parse reading plans.
- **Database**: SQLite based.

## Setup
1. Install requirements: pip install -r requirements.txt
2. Set .env: TELEGRAM_TOKEN, GOOGLE_API_KEY, CHAT_IDs

## Usage
Run: python send_bible_passage_all.py
Parse Plan: python tools/gemini_parser.py [Year] [Month]
