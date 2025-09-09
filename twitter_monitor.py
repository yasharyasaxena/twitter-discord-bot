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
async def main():
    bot = TwitterDiscordBotV2()  # Use rate-limited version
    await bot.run_monitoring_cycle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())