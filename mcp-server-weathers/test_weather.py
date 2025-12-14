#!/usr/bin/env python3
"""Test script for weather functions."""

import asyncio
import sys
from weather import get_alerts, get_forecast


async def test_alerts(state: str):
    """Test the get_alerts function."""
    print(f"Getting alerts for state: {state}")
    result = await get_alerts(state)
    print("Alerts:")
    print(result)
    print("\n" + "="*50 + "\n")


async def test_forecast(lat: float, lon: float):
    """Test the get_forecast function."""
    print(f"Getting forecast for location: {lat}, {lon}")
    result = await get_forecast(lat, lon)
    print("Forecast:")
    print(result)
    print("\n" + "="*50 + "\n")


async def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_weather.py alerts <STATE>")
        print("  python test_weather.py forecast <LAT> <LON>")
        print("\nExamples:")
        print("  python test_weather.py alerts NY")
        print("  python test_weather.py forecast 40.7128 -74.0060")
        return

    command = sys.argv[1].lower()
    
    if command == "alerts":
        if len(sys.argv) < 3:
            print("Please provide a state code (e.g., NY)")
            return
        state = sys.argv[2].upper()
        await test_alerts(state)
    
    elif command == "forecast":
        if len(sys.argv) < 4:
            print("Please provide latitude and longitude")
            return
        try:
            lat = float(sys.argv[2])
            lon = float(sys.argv[3])
            await test_forecast(lat, lon)
        except ValueError:
            print("Latitude and longitude must be numbers")
            return
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: alerts, forecast")


if __name__ == "__main__":
    asyncio.run(main())
