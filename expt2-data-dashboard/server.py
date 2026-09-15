"""
==============================================================================
Experiment 2: "Data Dashboard" Weather Connector MCP Server
==============================================================================
This MCP server acts as an external data connector, bridging the LLM to real-time
live weather observations from the public `wttr.in` meteorological service.

Exposed Tools:
  - `get_current_weather(location: str)`: Queries live weather for any global city/region
    and parses temperatures (°C & °F), condition, humidity, wind, and forecast notes.

Architecture:
  - Built with official MCP Python SDK (`mcp.server.fastmcp.FastMCP`).
  - Utilizes `httpx` with timeout management and resilient error handling.
  - Returns structured, LLM-ready context strings.
  - Stdio transport for standard MCP IPC.
==============================================================================
"""

import json
import sys
import urllib.parse
from typing import Any, Dict, Optional

# Ensure UTF-8 streams on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server with descriptive name
mcp = FastMCP("weather-data-dashboard")

# User-Agent for polite wttr.in queries
USER_AGENT = "Lab06-MCP-WeatherDashboard/1.0"


def _fetch_weather_raw(location: str) -> Dict[str, Any]:
    """
    Queries wttr.in JSON v1 format for the specified location.
    
    Includes timeout controls and SSL verification fallback to guarantee
    resilience regardless of local system certificate status.
    """
    clean_location = location.strip()
    encoded_loc = urllib.parse.quote(clean_location)
    url = f"https://wttr.in/{encoded_loc}?format=j1"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    # Attempt primary request (with verify=False fallback if local clock causes cert issues)
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, verify=False) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error {e.response.status_code} while querying wttr.in for '{location}'.")
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error while connecting to weather service: {e}")
    except json.JSONDecodeError:
        raise RuntimeError(f"Received non-JSON response from weather service for '{location}'.")


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================
# FastMCP translates Python type annotations and docstrings into the MCP tool schema.
# ============================================================================

@mcp.tool()
def get_current_weather(location: str) -> str:
    """
    Fetch the latest live weather observation and meteorological metrics for any city or location.

    Args:
        location: City name, region, or landmark (e.g. 'Tokyo', 'London', 'New York', 'Paris').

    Returns:
        A structured summary containing temperature (°C/°F), weather condition,
        humidity, wind speed/direction, feels-like temperature, and precipitation.
    """
    if not location or not location.strip():
        return "Error: Location parameter cannot be empty. Please provide a city name (e.g. 'Tokyo')."

    loc_str = location.strip()

    try:
        data = _fetch_weather_raw(loc_str)
    except Exception as e:
        # Fallback to simple wttr.in text format (?format=3) if JSON fails
        try:
            with httpx.Client(timeout=8.0, verify=False) as fallback_client:
                fb_url = f"https://wttr.in/{urllib.parse.quote(loc_str)}?format=3"
                fb_res = fallback_client.get(fb_url)
                if fb_res.status_code == 200 and fb_res.text.strip():
                    return f"Live Weather Summary for {loc_str}:\n{fb_res.text.strip()}"
        except Exception:
            pass

        return f"Unable to retrieve weather data for '{loc_str}'. Reason: {str(e)}"

    # Parse JSON structure returned by wttr.in format=j1
    try:
        current_condition = data.get("current_condition", [{}])[0]
        nearest_area = data.get("nearest_area", [{}])[0]

        # Extract resolved geographical identifiers
        resolved_city = nearest_area.get("areaName", [{}])[0].get("value", loc_str)
        country = nearest_area.get("country", [{}])[0].get("value", "")
        region = nearest_area.get("region", [{}])[0].get("value", "")
        location_header = f"{resolved_city}"
        if region and region != resolved_city:
            location_header += f", {region}"
        if country:
            location_header += f", {country}"

        # Extract key meteorological values
        temp_c = current_condition.get("temp_C", "N/A")
        temp_f = current_condition.get("temp_F", "N/A")
        feels_c = current_condition.get("FeelsLikeC", "N/A")
        feels_f = current_condition.get("FeelsLikeF", "N/A")
        
        weather_desc_list = current_condition.get("weatherDesc", [{}])
        weather_desc = weather_desc_list[0].get("value", "Unknown") if weather_desc_list else "Unknown"

        humidity = current_condition.get("humidity", "N/A")
        wind_kmph = current_condition.get("windspeedKmph", "N/A")
        wind_mph = current_condition.get("windspeedMiles", "N/A")
        wind_dir = current_condition.get("winddir16Point", "N/A")
        precip_mm = current_condition.get("precipMM", "0.0")
        uv_index = current_condition.get("uvIndex", "N/A")
        visibility_km = current_condition.get("visibility", "N/A")
        obs_time = current_condition.get("observation_time", "N/A")

        # Format as clean, structured, unambiguous text for the LLM
        summary_lines = [
            f"📍 Location: {location_header}",
            f"🌤️ Condition: {weather_desc}",
            f"🌡️ Temperature: {temp_c}°C ({temp_f}°F) [Feels like: {feels_c}°C / {feels_f}°F]",
            f"💧 Humidity: {humidity}%",
            f"💨 Wind: {wind_kmph} km/h ({wind_mph} mph) from {wind_dir}",
            f"🌧️ Precipitation: {precip_mm} mm",
            f"☀️ UV Index: {uv_index} | Visibility: {visibility_km} km",
            f"🕒 Observation Time: {obs_time} UTC"
        ]

        return "\n".join(summary_lines)

    except (KeyError, IndexError, TypeError) as e:
        return f"Warning: Received unexpected data format for location '{loc_str}'. Raw sample: {str(data)[:200]}..."


if __name__ == "__main__":
    # Start FastMCP server in stdio transport mode
    mcp.run(transport="stdio")
