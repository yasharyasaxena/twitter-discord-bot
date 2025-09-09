#!/usr/bin/env python3
"""
Automated scheduler for Free Tier Twitter Bot
Runs every 20 minutes automatically with proper rate limiting
"""

import asyncio
import time
from datetime import datetime, timedelta
from free_tier_bot import FreeTierTwitterBot
import os

class FreeTwitterScheduler:
    def __init__(self):
        self.bot = FreeTierTwitterBot()
        self.run_interval_minutes = 20  # Run every 20 minutes (safe buffer)
        
    def wait_for_next_safe_time(self):
        """Wait until it's safe to make the next request"""
        
        try:
            with open('last_request_time.txt', 'r') as f:
                last_request = datetime.fromisoformat(f.read().strip())
                
            next_safe_time = last_request + timedelta(minutes=16)  # 16 min minimum wait
            now = datetime.now()
            
            if now < next_safe_time:
                wait_seconds = (next_safe_time - now).total_seconds()
                print(f"⏳ Waiting {wait_seconds:.0f} seconds until next safe request...")
                print(f"🕐 Next request at: {next_safe_time.strftime('%H:%M:%S')}")
                
                # Show countdown
                while wait_seconds > 0:
                    mins, secs = divmod(int(wait_seconds), 60)
                    print(f"\r   Time remaining: {mins:02d}:{secs:02d}", end="", flush=True)
                    time.sleep(1)
                    wait_seconds -= 1
                
                print(f"\n✅ Safe to proceed at {datetime.now().strftime('%H:%M:%S')}")
                
        except FileNotFoundError:
            print("📝 No previous requests found - safe to proceed")
    
    async def run_continuous_monitoring(self):
        """Run continuous monitoring with proper timing"""
        
        print("🔄 Free Tier Twitter Scheduler")
        print(f"⏰ Started at: {datetime.now()}")
        print(f"📊 Will run every {self.run_interval_minutes} minutes")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 60)
        
        cycle = 0
        
        try:
            while True:
                cycle += 1
                print(f"\n🔄 Cycle #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 40)
                
                # Wait if needed
                self.wait_for_next_safe_time()
                
                # Run the bot
                result = await self.bot.run_free_tier_monitoring()
                
                # Show result
                if result == "SUCCESS":
                    print("🎉 Cycle completed successfully!")
                elif "wait" in result.lower() or result == "RATE_LIMITED":
                    print("⏳ Rate limited - will wait and try again")
                elif "monthly limit" in result.lower():
                    print("📊 Monthly limit reached - stopping scheduler")
                    break
                else:
                    print(f"ℹ️ Cycle result: {result}")
                
                # Wait for next cycle
                next_cycle = datetime.now() + timedelta(minutes=self.run_interval_minutes)
                print(f"\n⏰ Next cycle at: {next_cycle.strftime('%H:%M:%S')}")
                print(f"💤 Sleeping for {self.run_interval_minutes} minutes...")
                
                await asyncio.sleep(self.run_interval_minutes * 60)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Scheduler stopped by user after {cycle} cycles")
            print(f"⏰ Total runtime: {datetime.now()}")
        
        except Exception as e:
            print(f"\n❌ Scheduler error: {e}")
    
    def show_status(self):
        """Show current status"""
        
        print("📊 Current Status")
        print("=" * 30)
        
        # Monthly usage
        try:
            usage_data = self.bot.get_monthly_usage()
            print(f"📈 Monthly usage: {usage_data['usage']}/100 tweets")
            print(f"📅 Current month: {usage_data['month']}")
            remaining = 100 - usage_data['usage']
            print(f"🔋 Remaining: {remaining} tweets")
        except Exception as e:
            print(f"❌ Could not get usage: {e}")
        
        # Last request time
        try:
            with open('last_request_time.txt', 'r') as f:
                last_request = datetime.fromisoformat(f.read().strip())
                
            time_since = datetime.now() - last_request
            next_safe = last_request + timedelta(minutes=16)
            
            print(f"🕐 Last request: {last_request.strftime('%H:%M:%S')}")
            print(f"⏱️  Time since: {time_since.total_seconds()/60:.1f} minutes")
            
            if datetime.now() >= next_safe:
                print("✅ Ready for next request")
            else:
                wait_time = (next_safe - datetime.now()).total_seconds() / 60
                print(f"⏳ Wait {wait_time:.1f} more minutes")
                
        except FileNotFoundError:
            print("🕐 No previous requests")
        
        # Last successful check
        try:
            with open(self.bot.last_check_file, 'r') as f:
                last_check = datetime.fromisoformat(f.read().strip())
                print(f"✅ Last successful check: {last_check.strftime('%H:%M:%S')}")
        except FileNotFoundError:
            print("📝 No successful checks yet")

async def main():
    """Main function with options"""
    
    import sys
    
    scheduler = FreeTwitterScheduler()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "status":
            scheduler.show_status()
            return
        elif command == "once":
            print("🔄 Running once...")
            await scheduler.bot.run_free_tier_monitoring()
            return
        elif command == "help":
            print("🤖 Free Tier Twitter Scheduler")
            print("\nUsage:")
            print("  python scheduler.py          - Run continuously")
            print("  python scheduler.py once     - Run once and exit") 
            print("  python scheduler.py status   - Show current status")
            print("  python scheduler.py help     - Show this help")
            return
    
    # Default: run continuously
    await scheduler.run_continuous_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
