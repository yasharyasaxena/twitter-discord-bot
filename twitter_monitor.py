import tweepy
import discord
import requests
import json
import os
from datetime import datetime, timedelta
import asyncio

import time
import random
from datetime import datetime, timedelta

class RateLimitHandler:
    """Handle Twitter API rate limits intelligently"""
    
    def __init__(self):
        self.last_request_time = None
        self.consecutive_errors = 0
        self.min_delay = 2  # Minimum delay between requests
    
    def wait_if_needed(self):
        """Wait before making next request"""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            wait_time = self.min_delay - elapsed
            
            if wait_time > 0:
                print(f"⏳ Waiting {wait_time:.1f}s before next request...")
                time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def handle_rate_limit(self):
        """Handle rate limit with exponential backoff"""
        self.consecutive_errors += 1
        
        # Exponential backoff: 2^errors minutes, max 15 minutes
        wait_minutes = min(2 ** self.consecutive_errors, 15)
        wait_seconds = wait_minutes * 60
        
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.8, 1.2)
        wait_seconds = int(wait_seconds * jitter)
        
        print(f"🚫 Rate limited! Waiting {wait_seconds//60}m {wait_seconds%60}s...")
        
        # For GitHub Actions, we can't wait too long, so skip this cycle
        if wait_seconds > 300:  # More than 5 minutes
            print("⏭️  Skipping this cycle due to rate limits")
            return False
        
        time.sleep(wait_seconds)
        return True
    
    def reset_errors(self):
        """Reset error count on successful request"""
        self.consecutive_errors = 0

# Updated TwitterDiscordBot with rate limiting
class TwitterDiscordBotV2(TwitterDiscordBot):
    def __init__(self):
        super().__init__()
        self.rate_limiter = RateLimitHandler()
    
    def get_recent_tweets_from_brands(self):
        """Fetch tweets with intelligent rate limiting"""
        since_time = self.get_last_check_time()
        all_tweets = []
        
        print(f"🔍 Checking {len(BRANDS_TO_MONITOR)} brands since {since_time}")
        
        for i, brand in enumerate(BRANDS_TO_MONITOR):
            try:
                # Wait before each request
                self.rate_limiter.wait_if_needed()
                
                print(f"   📱 Checking @{brand}...")
                
                tweets = self.twitter_client.search_recent_tweets(
                    query=f"from:{brand}",
                    tweet_fields=['created_at', 'author_id', 'public_metrics'],
                    user_fields=['username', 'name', 'profile_image_url'],
                    expansions=['author_id'],
                    max_results=5,
                    start_time=since_time
                )
                
                # Success - reset error counter
                self.rate_limiter.reset_errors()
                
                if tweets and tweets.data:
                    users = {user.id: user for user in tweets.includes['users']}
                    
                    for tweet in tweets.data:
                        user = users[tweet.author_id]
                        all_tweets.append({
                            'text': tweet.text,
                            'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                            'author': user.name,
                            'username': user.username,
                            'created_at': tweet.created_at,
                            'profile_image': user.profile_image_url,
                            'likes': tweet.public_metrics['like_count'],
                            'retweets': tweet.public_metrics['retweet_count']
                        })
                    
                    print(f"   ✅ Found {len(tweets.data)} tweets from @{brand}")
                else:
                    print(f"   ℹ️  No new tweets from @{brand}")
            
            except tweepy.TooManyRequests as e:
                print(f"   🚫 Rate limited on @{brand}")
                
                # Try to handle rate limit
                if not self.rate_limiter.handle_rate_limit():
                    print("   ⏭️  Skipping remaining brands this cycle")
                    break
                    
            except tweepy.Unauthorized:
                print(f"   ❌ @{brand}: Account private or doesn't exist")
                continue
                
            except Exception as e:
                print(f"   ❌ Error checking @{brand}: {e}")
                continue
        
        print(f"📊 Total tweets found: {len(all_tweets)}")
        return sorted(all_tweets, key=lambda x: x['created_at'])

# Use the improved version


# Configuration - Reduced list to avoid rate limits
BRANDS_TO_MONITOR = [
    "OpenAI",      # High priority
    "anthropic",   # High priority  
    "Google"       # High priority
    # Add more brands gradually as you test rate limits
    # "Microsoft",
    # "nvidia",
    # "huggingface"
]

class TwitterDiscordBot:
    def __init__(self):
        # Twitter API v2 setup
        self.twitter_client = tweepy.Client(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
        )
        
        # Discord setup
        self.discord_token = os.getenv('DISCORD_BOT_TOKEN')
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.target_channel_id = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
        self.target_user_id = int(os.getenv('DISCORD_USER_ID', '0'))
        
        # Store last check time
        self.last_check_file = 'last_check.txt'
    
    def get_last_check_time(self):
        """Get the last time we checked for tweets"""
        try:
            with open(self.last_check_file, 'r') as f:
                return datetime.fromisoformat(f.read().strip())
        except FileNotFoundError:
            # For GitHub Actions, start fresh each time with 30 minutes ago
            return datetime.now() - timedelta(minutes=30)
    
    def save_last_check_time(self):
        """Save current time as last check time"""
        with open(self.last_check_file, 'w') as f:
            f.write(datetime.now().isoformat())
    
    def get_recent_tweets_from_brands(self):
        """Fetch recent tweets from monitored brands"""
        since_time = self.get_last_check_time()
        all_tweets = []
        
        for brand in BRANDS_TO_MONITOR:
            try:
                # Search for recent tweets from this brand
                tweets = self.twitter_client.search_recent_tweets(
                    query=f"from:{brand}",
                    tweet_fields=['created_at', 'author_id', 'public_metrics'],
                    user_fields=['username', 'name', 'profile_image_url'],
                    expansions=['author_id'],
                    max_results=10,
                    start_time=since_time
                )
                
                if tweets.data:
                    # Get user info
                    users = {user.id: user for user in tweets.includes['users']}
                    
                    for tweet in tweets.data:
                        user = users[tweet.author_id]
                        all_tweets.append({
                            'text': tweet.text,
                            'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                            'author': user.name,
                            'username': user.username,
                            'created_at': tweet.created_at,
                            'profile_image': user.profile_image_url,
                            'likes': tweet.public_metrics['like_count'],
                            'retweets': tweet.public_metrics['retweet_count']
                        })
            
            except Exception as e:
                print(f"Error fetching tweets for {brand}: {e}")
                continue
        
        return sorted(all_tweets, key=lambda x: x['created_at'])
    
    def send_webhook_notification(self, tweet_data):
        """Send notification via Discord webhook"""
        embed = {
            "title": f"New Tweet from @{tweet_data['username']}",
            "description": tweet_data['text'],
            "url": tweet_data['url'],
            "color": 1942002,  # Twitter blue
            "timestamp": tweet_data['created_at'].isoformat(),
            "author": {
                "name": tweet_data['author'],
                "icon_url": tweet_data['profile_image']
            },
            "fields": [
                {
                    "name": "❤️ Likes",
                    "value": str(tweet_data['likes']),
                    "inline": True
                },
                {
                    "name": "🔄 Retweets", 
                    "value": str(tweet_data['retweets']),
                    "inline": True
                }
            ]
        }
        
        payload = {
            "embeds": [embed],
            "username": "Twitter Monitor",
            "avatar_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png"
        }
        
        response = requests.post(self.webhook_url, json=payload)
        return response.status_code == 204
    
    async def send_discord_dm(self, tweet_data):
        """Send DM to specific user via Discord bot"""
        if not self.target_user_id:
            return False
            
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)
        
        @client.event
        async def on_ready():
            try:
                user = await client.fetch_user(self.target_user_id)
                
                embed = discord.Embed(
                    title=f"New Tweet from @{tweet_data['username']}", 
                    description=tweet_data['text'],
                    url=tweet_data['url'],
                    color=0x1DA1F2,
                    timestamp=tweet_data['created_at']
                )
                
                embed.set_author(
                    name=tweet_data['author'],
                    icon_url=tweet_data['profile_image']
                )
                
                embed.add_field(name="❤️ Likes", value=tweet_data['likes'], inline=True)
                embed.add_field(name="🔄 Retweets", value=tweet_data['retweets'], inline=True)
                
                await user.send(embed=embed)
                print(f"DM sent to user {self.target_user_id}")
                
            except Exception as e:
                print(f"Error sending DM: {e}")
            finally:
                await client.close()
        
        await client.start(self.discord_token)
    
    async def run_monitoring_cycle(self):
        """Run one monitoring cycle"""
        print(f"Starting monitoring cycle at {datetime.now()}")
        
        # Get recent tweets
        recent_tweets = self.get_recent_tweets_from_brands()
        
        if not recent_tweets:
            print("No new tweets found")
            return
        
        print(f"Found {len(recent_tweets)} new tweets")
        
        # Process each tweet
        for tweet in recent_tweets:
            # Send webhook notification
            webhook_success = self.send_webhook_notification(tweet)
            print(f"Webhook sent: {webhook_success}")
            
            # Send DM if configured
            if self.target_user_id:
                await self.send_discord_dm(tweet)
            
            # Small delay between notifications
            await asyncio.sleep(1)
        
        # Update last check time
        self.save_last_check_time()
        print("Monitoring cycle completed")

async def main():
    bot = TwitterDiscordBotV2()  # Use rate-limited version
    await bot.run_monitoring_cycle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())