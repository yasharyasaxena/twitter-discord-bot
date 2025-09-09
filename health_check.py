import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_test_webhook():
    """Send a test message via Discord webhook to check if workflow is working"""
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not found in environment variables")
        return False
    
    # Create test message
    embed = {
        "title": "🔍 Health Check - GitHub Workflow Test",
        "description": "Hi! This is a test message to verify the GitHub workflow is working properly.",
        "color": 65280,  # Green color
        "timestamp": datetime.now().isoformat(),
        "fields": [
            {
                "name": "Status",
                "value": "✅ Workflow Active",
                "inline": True
            },
            {
                "name": "Time",
                "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "inline": True
            }
        ],
        "footer": {
            "text": "Twitter Monitor Health Check"
        }
    }
    
    payload = {
        "embeds": [embed],
        "username": "Health Check Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2697/2697432.png"
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print("✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Failed to send message. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting health check...")
    success = send_test_webhook()
    if success:
        print("🎉 Health check completed successfully!")
    else:
        print("💥 Health check failed!")