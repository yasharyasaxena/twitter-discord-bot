import tweepy
import discord
import requests
import json
import os
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
from time import sleep

# Load environment variables from .env file
load_dotenv()

# Configuration
BRANDS_TO_MONITOR = [
    "bundleddesign",
]

print("Loaded brands to monitor:", BRANDS_TO_MONITOR)

BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('TWITTER_TOKEN_SECRET')

if not all([BEARER_TOKEN, CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
    print("Missing Twitter API credentials:")
    if not BEARER_TOKEN:
        print(" - TWITTER_BEARER_TOKEN")
    if not CONSUMER_KEY:
        print(" - TWITTER_CONSUMER_KEY")
    if not CONSUMER_SECRET:
        print(" - TWITTER_CONSUMER_SECRET")
    if not ACCESS_TOKEN:
        print(" - TWITTER_ACCESS_TOKEN")
    if not ACCESS_TOKEN_SECRET:
        print(" - TWITTER_TOKEN_SECRET")
    raise ValueError("One or more Twitter API credentials are missing in environment variables.")

class TwitterDiscordBot:
    def __init__(self):
        # Twitter API v2 setup
        self.twitter_client = tweepy.Client(
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
            consumer_key=os.getenv('TWITTER_CONSUMER_KEY'),
            consumer_secret=os.getenv('TWITTER_CONSUMER_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_TOKEN_SECRET'),
            wait_on_rate_limit=True
        )
        
        # Discord setup
        self.discord_token = os.getenv('DISCORD_BOT_TOKEN')
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.target_channel_id = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
        self.target_user_id = int(os.getenv('DISCORD_USER_ID', '0'))
        
        # Store last tweet ID
        self.last_id_file = 'last_tweet_id.txt'

    def get_last_tweet_id(self):
        """Get the last tweet ID we checked"""
        try:
            with open(self.last_id_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            return None
    
    def save_last_tweet_id(self, tweet_id):
        """Save the latest tweet ID"""
        with open(self.last_id_file, 'w') as f:
            f.write(str(tweet_id))
    
    def get_user_id_by_username(self, username):
        """Get user ID from username"""
        try:
            user = self.twitter_client.get_user(username=username)
            print(f"Fetched user ID for {username}: {user.data.id}")
            return user.data.id if user.data else None
        except Exception as e:
            print(f"Error getting user ID for {username}: {e}")
            return None
    
    def get_tweets_by_user_id(self, user_id, since_id=None, max_results=10):
        """Get tweets from a user ID since specified tweet ID"""
        try:
            kwargs = {
                'id': user_id,
                'tweet_fields': ['created_at', 'author_id', 'public_metrics'],
                'user_fields': ['username', 'name', 'profile_image_url'],
                'expansions': ['author_id'],
                'max_results': max_results,
            }
            
            if since_id:
                kwargs['since_id'] = since_id
            
            tweets = self.twitter_client.get_users_tweets(**kwargs)
            print(f"Fetched tweets for user ID {user_id}: {tweets}")
            return tweets
        except Exception as e:
            print(f"Error fetching tweets for user ID {user_id}: {e}")
            return None
    
    def get_recent_tweets_from_brands(self):
        """Fetch recent tweets from monitored brands"""
        since_id = self.get_last_tweet_id()
        
        print(f"Current time: {datetime.now()}")
        print(f"Checking for tweets since ID: {since_id}")
        all_tweets = []
        
        for brand in BRANDS_TO_MONITOR:
            tweets_found = False
            
            try:
                # Primary method: Search for recent tweets from this brand
                kwargs = {
                    'query': f"from:{brand}",
                    'tweet_fields': ['created_at', 'author_id', 'public_metrics'],
                    'user_fields': ['username', 'name', 'profile_image_url'],
                    'expansions': ['author_id'],
                    'max_results': 10,
                }
                
                if since_id:
                    kwargs['since_id'] = since_id
                
                tweets = self.twitter_client.search_recent_tweets(**kwargs)
                
                if tweets.data:
                    tweets_found = True
                    # Get user info
                    users = {user.id: user for user in tweets.includes['users']}
                    
                    for tweet in tweets.data:
                        user = users[tweet.author_id]
                        all_tweets.append({
                            'id': tweet.id,
                            'text': tweet.text,
                            'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                            'author': user.name,
                            'username': user.username,
                            'created_at': tweet.created_at,
                            'profile_image': user.profile_image_url,
                            'likes': tweet.public_metrics['like_count'],
                            'retweets': tweet.public_metrics['retweet_count']
                        })
                
                # Failsafe: If no tweets found, try getting user ID and fetch directly
                if not tweets_found:
                    print(f"No tweets found via search for {brand}, trying failsafe method...")
                    user_id = self.get_user_id_by_username(brand)
                    
                    if user_id:
                        print(f"Found user ID {user_id} for {brand}, fetching tweets...")
                        user_tweets = self.get_tweets_by_user_id(user_id, since_id)
                        
                        if user_tweets and user_tweets.data:
                            # Get user info for the failsafe method
                            user_info = self.twitter_client.get_user(id=user_id, 
                                                                   user_fields=['username', 'name', 'profile_image_url'])
                            
                            if user_info.data:
                                user = user_info.data
                                for tweet in user_tweets.data:
                                    all_tweets.append({
                                        'id': tweet.id,
                                        'text': tweet.text,
                                        'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                                        'author': user.name,
                                        'username': user.username,
                                        'created_at': tweet.created_at,
                                        'profile_image': user.profile_image_url,
                                        'likes': tweet.public_metrics['like_count'],
                                        'retweets': tweet.public_metrics['retweet_count']
                                    })
                                print(f"Failsafe method found {len(user_tweets.data)} tweets for {brand}")
                    else:
                        print(f"Could not find user ID for {brand}")
            
            except Exception as e:
                print(f"Error fetching tweets for {brand}: {e}")
                # Try failsafe method even if primary method fails
                try:
                    print(f"Primary method failed for {brand}, trying failsafe...")
                    user_id = self.get_user_id_by_username(brand)
                    
                    if user_id:
                        user_tweets = self.get_tweets_by_user_id(user_id, since_id)
                        
                        if user_tweets and user_tweets.data:
                            user_info = self.twitter_client.get_user(id=user_id,
                                                                   user_fields=['username', 'name', 'profile_image_url'])
                            
                            if user_info.data:
                                user = user_info.data
                                for tweet in user_tweets.data:
                                    all_tweets.append({
                                        'id': tweet.id,
                                        'text': tweet.text,
                                        'url': f"https://twitter.com/{user.username}/status/{tweet.id}",
                                        'author': user.name,
                                        'username': user.username,
                                        'created_at': tweet.created_at,
                                        'profile_image': user.profile_image_url,
                                        'likes': tweet.public_metrics['like_count'],
                                        'retweets': tweet.public_metrics['retweet_count']
                                    })
                                print(f"Failsafe method recovered {len(user_tweets.data)} tweets for {brand}")
                except Exception as failsafe_error:
                    print(f"Failsafe method also failed for {brand}: {failsafe_error}")
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
        
        # Process each tweet and track the highest ID
        highest_tweet_id = None
        
        for tweet in recent_tweets:
            # Send webhook notification
            webhook_success = self.send_webhook_notification(tweet)
            print(f"Webhook sent: {webhook_success}")
            
            # Send DM if configured - DISABLED (using webhooks only)
            # if self.target_user_id:
            #     await self.send_discord_dm(tweet)
            
            # Track highest tweet ID (tweet IDs are strings but can be compared as integers)
            tweet_id_str = str(tweet['id'])
            if not highest_tweet_id or int(tweet_id_str) > int(highest_tweet_id):
                highest_tweet_id = tweet_id_str
            
            # Small delay between notifications
            await asyncio.sleep(1)
        
        # Update last tweet ID if we processed any tweets
        if highest_tweet_id:
            self.save_last_tweet_id(highest_tweet_id)
            print(f"Updated last tweet ID to: {highest_tweet_id}")
        
        print("Monitoring cycle completed")

async def main():
    bot = TwitterDiscordBot()
    await bot.run_monitoring_cycle()

if __name__ == "__main__":
    asyncio.run(main())