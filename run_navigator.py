# run_navigator.py
import asyncio
import argparse
from main import main as start_web_app
from step5_navigator import NavigatorModule
import json

async def _analyze(repo_url: str):
    """Run the async analysis and return the navigator instance (for potential further use)."""
    print(f"Analyzing repository: {repo_url}")
    navigator = NavigatorModule()

    try:
        report = await navigator.analyze_repository(repo_url)
        print("Analysis completed!")
        print(json.dumps(report, indent=2))

        # Save results
        navigator.save_analysis()
        return navigator

    except Exception as e:
        print(f"Error during analysis: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CodeIQ Navigator")
    parser.add_argument("--repo", help="GitHub repository URL to analyze")
    parser.add_argument("--headless", action="store_true", help="Run without web interface")
    
    args = parser.parse_args()

    # Run analysis in the event loop, then start the web server synchronously.
    if args.repo:
        asyncio.run(_analyze(args.repo))

    if not args.headless:
        # This will create and run the uvicorn server (synchronous call)
        start_web_app()