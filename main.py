"""
Entry point for the Carbon Watch Agent.
Scheduling is handled externally by GitHub Actions (.github/workflows/).
"""

from src.agent import run_agent

if __name__ == "__main__":
    run_agent()
