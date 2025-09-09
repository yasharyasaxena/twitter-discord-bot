#!/usr/bin/env python3
"""
Perfect Twitter bot for Free Tier (1 request per 15 minutes)
Optimized for 100 tweets/month limit
"""

from dotenv import load_dotenv
import tweepy
import requests
import os
import time
from datetime import datetime, timedelta
import asyncio
import json

load_dotenv()

class FreeTierTwitterBot:
    def __init__(self):
        self.twitter_client = tweepy.Client(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
        )
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        
        # File tracking
        self.last_check_file = 'last_check.txt'
        self.usage_tracking_file = 'monthly_usage.txt'
        
        # Free tier limits
        self.monthly_limit = 100  # tweets per month
        self.rate_limit_minutes = 16  # Wait 16 minutes between requests (to be safe)
        
        # Brands to monitor (you can adjust this)
        self.brands = ["OpenAI", "anthropic"]  # Reduced to 2 most important
    
    def get_monthly_usage(self):
        """Track monthly usage to stay under 100 tweets"""
        try:
            with open(self.usage_tracking_file, 'r') as f:
                data = json.load(f)
                
            current_month = datetime.now().strftime('%Y-%m')
            
            if data.get('month') != current_month:
                # New month, reset usage
                data = {'month': current_month, 'usage': 0}
            
            return data
        except FileNotFoundError:
            current_month = datetime.now().strftime('%Y-%m')
            return {'month': current_month, 'usage': 0}
    
    def save_usage(self, tweets_fetched):
        """Save usage tracking"""
        usage_data = self.get_monthly_usage()
        usage_data['usage'] += tweets_fetched
        
        with open(self.usage_tracking_file, 'w') as f:
            json.dump(usage_data, f)
    
    def can_make_request(self):
        """Check if we can safely make a request"""
        
        # Check monthly usage
        usage_data = self.get_monthly_usage()
        if usage_data['usage'] >= self.monthly_limit:
            print(f"❌ Monthly limit reached: {usage_data['usage']}/{self.monthly_limit}")
            return False, f"Monthly limit reached ({usage_data['usage']}/{self.monthly_limit})"
        
        # Check time since last request
        try:
            with open('last_request_time.txt', 'r') as f:
                last_request = datetime.fromisoformat(f.read().strip())
                
            time_since = (datetime.now() - last_request).total_seconds() / 60
            
            if time_since < self.rate_limit_minutes:
                wait_time = self.rate_limit_minutes - time_since
                return False, f"Rate limited: wait {wait_time:.1f} more minutes"
                
        except FileNotFoundError:
            pass  # First run, OK to proceed
        
        remaining = self.monthly_limit - usage_data['usage']
        return True, f"OK to proceed ({remaining} tweets remaining this month)"
    
    def save_request_time(self):
        """Save when we made a request"""
        with open('last_request_time.txt', 'w') as f:
            f.write(datetime.now().isoformat())
    
    def get_last_check_time(self):
        """Get last successful check time"""
        try:
            with open(self.last_check_file, 'r') as f:
                return datetime.fromisoformat(f.read().strip())
        except FileNotFoundError:
            # Start with last 6 hours for first run
            return datetime.now() - timedelta(hours=6)
    
    def save_last_check_time(self):
        """Save current time as last check time"""
        with open(self.last_check_file, 'w') as f:
            f.write(datetime.now().isoformat())
    
    def smart_tweet_search(self):
        """Optimized search for free tier"""
        
        since_time = self.get_last_check_time()
        
        # Use minimal query to maximize results per request
        query = " OR ".join([f"from:{brand}" for brand in self.brands])
        
        print(f"🔍 Query: {query}")
        print(f"📅 Since: {since_time}")
        
        try:
            # Single request with minimal fields to save on quota
            response = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,  # Maximum allowed
                start_time=since_time,
                tweet_fields=['created_at', 'author_id'],
                user_fields=['username'],
                expansions=['author_id']
            )
            
            tweets = []
            
            if response.data:
                # Get user mapping
                users = {user.id: user for user in response.includes['users']}
                
                for tweet in response.data:
                    user = users.get(tweet.author_id)
                    username = user.username if user else 'unknown'
                    
                    tweets.append({
                        'text': tweet.text,
                        'url': f"https://twitter.com/{username}/status/{tweet.id}",
                        'author': username,
                        'username': username,
                        'created_at': tweet.created_at
                    })
                
                print(f"✅ Found {len(tweets)} tweets")
                
                # Track usage
                self.save_usage(len(tweets))
                self.save_request_time()
                
            return tweets
            
        except tweepy.TooManyRequests:
            print("❌ Rate limited by Twitter")
            self.save_request_time()  # Record that we made a request
            return "RATE_LIMITED"
        except Exception as e:
            print(f"❌ Error: {e}")
            return "ERROR"
    
    def send_webhook(self, tweet_data):
        """Send Discord webhook notification"""
        try:
            content = (
                f"🐦 **New Tweet from @{tweet_data['username']}**\n\n"
                f"{tweet_data['text']}\n\n"
                f"🔗 {tweet_data['url']}\n"
                f"⏰ {tweet_data['created_at']}"
            )
            
            payload = {
                "content": content,
                "username": "Twitter Monitor (Free Tier)"
            }
            
            response = requests.post(self.webhook_url, json=payload)
            return response.status_code == 204
        except Exception as e:
            print(f"Error sending webhook: {e}")
            return False
    
    async def run_free_tier_monitoring(self):
        """Run monitoring optimized for free tier"""
        
        print("🆓 Free Tier Twitter Monitor")
        print(f"⏰ {datetime.now()}")
        print("=" * 50)
        
        # Check if we can make a request
        can_proceed, message = self.can_make_request()
        
        usage_data = self.get_monthly_usage()
        print(f"📊 Monthly usage: {usage_data['usage']}/{self.monthly_limit}")
        print(f"🔄 Status: {message}")
        
        if not can_proceed:
            return message
        
        # Make the request
        print("\n🚀 Making API request...")
        tweets = self.smart_tweet_search()
        
        if tweets == "RATE_LIMITED":
            return "RATE_LIMITED"
        elif tweets == "ERROR":
            return "ERROR"
        elif not tweets:
            print("ℹ️ No new tweets found")
            self.save_last_check_time()
            return "NO_TWEETS"
        
        # Process tweets
        print(f"\n📬 Processing {len(tweets)} tweets...")
        
        for i, tweet in enumerate(tweets):
            try:
                success = self.send_webhook(tweet)
                status = "✅" if success else "❌"
                print(f"   {status} {i+1}/{len(tweets)}: @{tweet['username']}")
                
                # Small delay between webhooks
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error with tweet {i+1}: {e}")
        
        # Update last check time
        self.save_last_check_time()
        
        # Show next allowed request time
        next_request = datetime.now() + timedelta(minutes=self.rate_limit_minutes)
        print(f"\n⏰ Next request allowed after: {next_request.strftime('%H:%M:%S')}")
        
        return "SUCCESS"

async def main():
    """Main function"""
    
    print("🤖 Free Tier Twitter Discord Bot")
    
    # Check environment
    if not os.getenv('TWITTER_BEARER_TOKEN'):
        print("❌ Missing TWITTER_BEARER_TOKEN")
        return
    
    if not os.getenv('DISCORD_WEBHOOK_URL'):
        print("❌ Missing DISCORD_WEBHOOK_URL")
        return
    
    # Run bot
    bot = FreeTierTwitterBot()
    result = await bot.run_free_tier_monitoring()
    
    print(f"\n🏁 Result: {result}")
    
    if result == "SUCCESS":
        print("\n🎉 Monitoring completed successfully!")
    elif "wait" in result.lower():
        print(f"\n⏳ {result}")
    elif result == "RATE_LIMITED":
        print("\n🚫 Rate limited - wait 16+ minutes before next run")
    
    print("\n💡 Free Tier Tips:")
    print("   • Run maximum once every 16+ minutes")
    print("   • 100 tweets max per month")
    print("   • Consider upgrading to Basic ($100/month) for better limits")

if __name__ == "__main__":
    asyncio.run(main())
