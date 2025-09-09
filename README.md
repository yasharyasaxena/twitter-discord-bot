# Twitter Discord Bot - Clean Setup

## 📁 **Files in this Repository**

### **Essential Files (Keep These)**

- **`free_tier_bot.py`** - Main bot optimized for Twitter Free Tier
- **`scheduler.py`** - Automated scheduler that runs the bot every 20 minutes
- **`config.py`** - Configuration settings for brands and rate limits
- **`requirements.txt`** - Python dependencies
- **`.env`** - Your API keys and tokens (keep private!)
- **`SOLUTION.md`** - Complete documentation and setup guide

### **System Files (Don't Touch)**

- **`.git/`** - Git version control
- **`.github/`** - GitHub Actions workflow
- **`.gitignore`** - Files to ignore in Git

## 🚀 **Quick Start**

### **1. One-Time Setup**

```cmd
pip install -r requirements.txt
```

### **2. Run the Bot**

**Option A: Run Once**

```cmd
python free_tier_bot.py
```

**Option B: Run Continuously (Recommended)**

```cmd
python scheduler.py
```

**Option C: Check Status**

```cmd
python scheduler.py status
```

## 📊 **What This Bot Does**

- **Monitors**: OpenAI and Anthropic Twitter accounts
- **Frequency**: Every 20 minutes (respects free tier limits)
- **Notifications**: Sends Discord webhooks for new tweets
- **Smart**: Tracks usage to stay under 100 tweets/month limit
- **Safe**: Never hits rate limits

## 🔧 **Configuration**

Edit `config.py` to:

- Change which accounts to monitor
- Adjust timing settings
- Modify Discord notification settings

## ✅ **This is Production Ready**

The bot is optimized for Twitter's Free Tier and will run reliably without hitting rate limits!

Just run `python scheduler.py` and let it work automatically. 🎯
