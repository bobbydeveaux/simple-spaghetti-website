"""
OpenWeatherMap API Client

This module provides a client for fetching weather data from the OpenWeatherMap API
to support weather data ingestion for F1 race analytics.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, Union

import aiohttp
from pydantic import BaseModel, Field

from app.config import get_settings


logger = logging.getLogger(__name__)


class WeatherData(BaseModel):
    """Weather data model for OpenWeatherMap API responses."""

    temperature_celsius: Decimal = Field(..., description="Temperature in Celsius")
    precipitation_mm: Decimal = Field(default=Decimal('0'), description="Precipitation in millimeters")
    wind_speed_kph: Decimal = Field(..., description="Wind speed in kilometers per hour")
    conditions: str = Field(..., description="Weather condition description")
    humidity_percent: Optional[int] = Field(None, description="Humidity percentage")
    pressure_hpa: Optional[int] = Field(None, description="Atmospheric pressure in hPa")
    visibility_km: Optional[Decimal] = Field(None, description="Visibility in kilometers")
    timestamp: datetime = Field(..., description="Timestamp of weather data")


class OpenWeatherMapClient:
    """Client for OpenWeatherMap API integration."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize the OpenWeatherMap client.

        Args:
            api_key: OpenWeatherMap API key. If None, will use config value.
            base_url: Base URL for OpenWeatherMap API. If None, will use config value.
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.external_apis.weather_api_key
        self.base_url = base_url or self.settings.external_apis.weather_base_url

        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is required")

    async def get_current_weather(
        self,
        latitude: Union[float, Decimal],
        longitude: Union[float, Decimal]
    ) -> WeatherData:
        """Get current weather data for given coordinates.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            WeatherData object with current weather information

        Raises:
            aiohttp.ClientError: If API request fails
            ValueError: If response data is invalid
        """
        url = f"{self.base_url}/weather"
        params = {
            'lat': float(latitude),
            'lon': float(longitude),
            'appid': self.api_key,
            'units': 'metric'  # Use Celsius for temperature
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 401:
                        raise ValueError("Invalid OpenWeatherMap API key")
                    if response.status == 429:
                        raise ValueError("OpenWeatherMap API rate limit exceeded")

                    response.raise_for_status()
                    data = await response.json()

                    return self._parse_current_weather(data)

            except aiohttp.ClientError as e:
                logger.error(f"Failed to fetch current weather: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching current weather: {e}")
                raise

    async def get_historical_weather(
        self,
        latitude: Union[float, Decimal],
        longitude: Union[float, Decimal],
        timestamp: datetime
    ) -> WeatherData:
        """Get historical weather data for given coordinates and time.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            timestamp: Historical timestamp (UTC)

        Returns:
            WeatherData object with historical weather information

        Raises:
            aiohttp.ClientError: If API request fails
            ValueError: If response data is invalid or timestamp is too recent
        """
        # Convert datetime to Unix timestamp
        unix_timestamp = int(timestamp.timestamp())

        # Historical weather API endpoint
        url = f"{self.base_url}/onecall/timemachine"
        params = {
            'lat': float(latitude),
            'lon': float(longitude),
            'dt': unix_timestamp,
            'appid': self.api_key,
            'units': 'metric'
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 401:
                        raise ValueError("Invalid OpenWeatherMap API key")
                    if response.status == 429:
                        raise ValueError("OpenWeatherMap API rate limit exceeded")
                    if response.status == 400:
                        error_data = await response.json()
                        if "dt" in error_data.get("message", ""):
                            raise ValueError("Historical data not available for this timestamp")

                    response.raise_for_status()
                    data = await response.json()

                    return self._parse_historical_weather(data)

            except aiohttp.ClientError as e:
                logger.error(f"Failed to fetch historical weather: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching historical weather: {e}")
                raise

    async def get_weather_forecast(
        self,
        latitude: Union[float, Decimal],
        longitude: Union[float, Decimal],
        days: int = 5
    ) -> list[WeatherData]:
        """Get weather forecast for given coordinates.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            days: Number of forecast days (1-5)

        Returns:
            List of WeatherData objects for forecast period

        Raises:
            aiohttp.ClientError: If API request fails
            ValueError: If response data is invalid or days is out of range
        """
        if not (1 <= days <= 5):
            raise ValueError("Forecast days must be between 1 and 5")

        url = f"{self.base_url}/forecast"
        params = {
            'lat': float(latitude),
            'lon': float(longitude),
            'appid': self.api_key,
            'units': 'metric',
            'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 401:
                        raise ValueError("Invalid OpenWeatherMap API key")
                    if response.status == 429:
                        raise ValueError("OpenWeatherMap API rate limit exceeded")

                    response.raise_for_status()
                    data = await response.json()

                    return self._parse_forecast_weather(data)

            except aiohttp.ClientError as e:
                logger.error(f"Failed to fetch weather forecast: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching weather forecast: {e}")
                raise

    def _parse_current_weather(self, data: Dict[str, Any]) -> WeatherData:
        """Parse current weather API response.

        Args:
            data: Raw API response data

        Returns:
            Parsed WeatherData object
        """
        main = data.get('main', {})
        weather = data.get('weather', [{}])[0]
        wind = data.get('wind', {})
        rain = data.get('rain', {})
        snow = data.get('snow', {})

        # Calculate precipitation (rain + snow)
        precipitation = Decimal('0')
        if '1h' in rain:
            precipitation += Decimal(str(rain['1h']))
        if '1h' in snow:
            precipitation += Decimal(str(snow['1h']))

        # Convert weather condition to our enum format
        weather_condition = self._map_weather_condition(weather.get('main', ''))

        # Convert wind speed from m/s to km/h
        wind_speed_ms = wind.get('speed', 0)
        wind_speed_kph = Decimal(str(wind_speed_ms)) * Decimal('3.6')

        return WeatherData(
            temperature_celsius=Decimal(str(main.get('temp', 0))),
            precipitation_mm=precipitation,
            wind_speed_kph=wind_speed_kph,
            conditions=weather_condition,
            humidity_percent=main.get('humidity'),
            pressure_hpa=main.get('pressure'),
            visibility_km=Decimal(str(data.get('visibility', 0) / 1000)) if data.get('visibility') else None,
            timestamp=datetime.now(timezone.utc)
        )

    def _parse_historical_weather(self, data: Dict[str, Any]) -> WeatherData:
        """Parse historical weather API response.

        Args:
            data: Raw API response data

        Returns:
            Parsed WeatherData object
        """
        current = data.get('current', {})
        weather = current.get('weather', [{}])[0]

        # Calculate precipitation
        precipitation = Decimal('0')
        if 'rain' in current and '1h' in current['rain']:
            precipitation += Decimal(str(current['rain']['1h']))
        if 'snow' in current and '1h' in current['snow']:
            precipitation += Decimal(str(current['snow']['1h']))

        # Convert weather condition to our enum format
        weather_condition = self._map_weather_condition(weather.get('main', ''))

        # Convert wind speed from m/s to km/h
        wind_speed_ms = current.get('wind_speed', 0)
        wind_speed_kph = Decimal(str(wind_speed_ms)) * Decimal('3.6')

        return WeatherData(
            temperature_celsius=Decimal(str(current.get('temp', 0))),
            precipitation_mm=precipitation,
            wind_speed_kph=wind_speed_kph,
            conditions=weather_condition,
            humidity_percent=current.get('humidity'),
            pressure_hpa=current.get('pressure'),
            visibility_km=Decimal(str(current.get('visibility', 0) / 1000)) if current.get('visibility') else None,
            timestamp=datetime.fromtimestamp(current.get('dt', 0), tz=timezone.utc)
        )

    def _parse_forecast_weather(self, data: Dict[str, Any]) -> list[WeatherData]:
        """Parse forecast weather API response.

        Args:
            data: Raw API response data

        Returns:
            List of parsed WeatherData objects
        """
        forecast_list = data.get('list', [])
        weather_data_list = []

        for item in forecast_list:
            main = item.get('main', {})
            weather = item.get('weather', [{}])[0]
            wind = item.get('wind', {})
            rain = item.get('rain', {})
            snow = item.get('snow', {})

            # Calculate precipitation
            precipitation = Decimal('0')
            if '3h' in rain:
                precipitation += Decimal(str(rain['3h']))
            if '3h' in snow:
                precipitation += Decimal(str(snow['3h']))

            # Convert weather condition to our enum format
            weather_condition = self._map_weather_condition(weather.get('main', ''))

            # Convert wind speed from m/s to km/h
            wind_speed_ms = wind.get('speed', 0)
            wind_speed_kph = Decimal(str(wind_speed_ms)) * Decimal('3.6')

            weather_data = WeatherData(
                temperature_celsius=Decimal(str(main.get('temp', 0))),
                precipitation_mm=precipitation,
                wind_speed_kph=wind_speed_kph,
                conditions=weather_condition,
                humidity_percent=main.get('humidity'),
                pressure_hpa=main.get('pressure'),
                visibility_km=None,  # Not available in forecast API
                timestamp=datetime.fromtimestamp(item.get('dt', 0), tz=timezone.utc)
            )
            weather_data_list.append(weather_data)

        return weather_data_list

    def _map_weather_condition(self, openweather_condition: str) -> str:
        """Map OpenWeatherMap weather condition to our enum values.

        Args:
            openweather_condition: OpenWeatherMap weather condition string

        Returns:
            Mapped weather condition for our system
        """
        condition_mapping = {
            'Clear': 'DRY',
            'Clouds': 'OVERCAST',
            'Rain': 'WET',
            'Drizzle': 'WET',
            'Thunderstorm': 'WET',
            'Snow': 'WET',
            'Mist': 'WET',
            'Fog': 'WET',
            'Haze': 'OVERCAST',
            'Dust': 'OVERCAST',
            'Sand': 'OVERCAST',
            'Ash': 'OVERCAST',
            'Squall': 'WET',
            'Tornado': 'WET'
        }

        return condition_mapping.get(openweather_condition, 'DRY')


# Convenience function for creating a client instance
def create_weather_client(api_key: Optional[str] = None) -> OpenWeatherMapClient:
    """Create a configured OpenWeatherMap client instance.

    Args:
        api_key: OpenWeatherMap API key. If None, will use config value.

    Returns:
        Configured OpenWeatherMapClient instance
    """
    return OpenWeatherMapClient(api_key=api_key)