# Configuration for Twitter Discord Bot (Free Tier Optimized)

# Brands to monitor (keep this list short for free tier)
BRANDS_TO_MONITOR = [
    "OpenAI",
    "anthropic"
    # Add more brands here, but remember: free tier has limits
    # Uncomment these if you want more:
    # "google",
    # "Microsoft"
]

# Free tier settings (optimized for actual Twitter limits)
RATE_LIMIT_SETTINGS = {
    # Time to wait between API requests (minutes) - Free tier: 1 request per 15 min
    'request_interval_minutes': 16,
    
    # Maximum tweets to fetch per request
    'max_tweets_per_request': 100,
    
    # Scheduler run interval (minutes) - how often to check if we can make requests
    'scheduler_interval': 20
}

# Discord notification settings
DISCORD_SETTINGS = {
    # Delay between Discord notifications (seconds)
    'notification_delay': 2,
    
    # Maximum retries for failed webhooks
    'max_retries': 3
}

# Twitter API Free Tier Limits (for reference)
FREE_TIER_LIMITS = {
    'requests_per_15_min': 1,        # Only 1 search request per 15 minutes
    'tweets_per_month': 100,         # 100 tweet reads per month
    'monthly_reset_day': 9           # Resets on 9th of each month
}
