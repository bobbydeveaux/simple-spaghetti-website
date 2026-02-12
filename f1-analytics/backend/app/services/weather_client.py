"""
OpenWeatherMap API client for F1 weather data.

This module provides a client for the OpenWeatherMap API to fetch historical
and forecast weather data for F1 race circuits.

API Documentation: https://openweathermap.org/api
Rate Limits: 1,000 calls/day (free tier), paid tiers available
"""

import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import ExternalAPIConfig

logger = logging.getLogger(__name__)


class WeatherAPIError(Exception):
    """Exception raised for weather API related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class CircuitCoordinates:
    """
    Circuit coordinate mappings for F1 circuits.

    These coordinates are used to fetch weather data for each circuit location.
    Coordinates are approximate circuit locations (lat, lon).
    """

    CIRCUITS = {
        # Current F1 circuits (2023-2024)
        'albert_park': (-37.8497, 144.968),  # Australian GP
        'bahrain': (26.0325, 50.5106),       # Bahrain GP
        'shanghai': (31.3389, 121.2197),     # Chinese GP
        'baku': (40.3725, 49.8533),          # Azerbaijan GP
        'miami': (25.9581, -80.2389),        # Miami GP
        'imola': (44.3439, 11.7167),         # Emilia-Romagna GP
        'monaco': (43.7347, 7.4197),         # Monaco GP
        'catalunya': (41.57, 2.2611),        # Spanish GP
        'montreal': (45.5017, -73.5297),     # Canadian GP
        'silverstone': (52.0786, -1.0169),   # British GP
        'hungaroring': (47.5789, 19.2486),   # Hungarian GP
        'spa': (50.4372, 5.9714),            # Belgian GP
        'zandvoort': (52.3888, 4.5408),      # Dutch GP
        'monza': (45.6156, 9.2811),          # Italian GP
        'singapore': (1.2914, 103.864),      # Singapore GP
        'suzuka': (34.8431, 136.5414),       # Japanese GP
        'losail': (25.49, 51.4542),          # Qatar GP
        'austin': (30.1328, -97.6411),       # US GP
        'rodriguez': (19.4042, -99.0907),    # Mexican GP
        'interlagos': (-23.7036, -46.6997),  # Brazilian GP
        'yas_marina': (24.4672, 54.6031),    # Abu Dhabi GP
        'jeddah': (21.6319, 39.1044),        # Saudi Arabian GP
        'las_vegas': (36.1147, -115.1728),   # Las Vegas GP

        # Historical circuits
        'nurburgring': (50.3356, 6.9475),    # Eifel GP
        'portimao': (37.227, -8.6267),       # Portuguese GP
        'istanbul': (40.9517, 29.405),       # Turkish GP
        'sochi': (43.4057, 39.9606),         # Russian GP
        'hockenheim': (49.3278, 8.5658),     # German GP
        'sepang': (2.7608, 101.7381),        # Malaysian GP
        'buddh': (28.3487, 77.5331),         # Indian GP
        'valencia': (39.4581, -0.3311),      # European GP
        'yeongam': (34.7339, 126.6708),      # Korean GP
        'fuji': (35.3717, 138.9272),         # Japanese GP (Fuji)
    }

    @classmethod
    def get_coordinates(cls, circuit_id: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for a circuit."""
        return cls.CIRCUITS.get(circuit_id.lower())

    @classmethod
    def get_all_circuits(cls) -> List[str]:
        """Get list of all available circuit IDs."""
        return list(cls.CIRCUITS.keys())


class WeatherClient:
    """
    Async client for OpenWeatherMap API.

    Provides methods to fetch weather data for F1 circuits including:
    - Historical weather data
    - Current weather conditions
    - 5-day weather forecasts
    - Weather data by coordinates
    """

    def __init__(self, config: Optional[ExternalAPIConfig] = None, session: Optional[httpx.AsyncClient] = None):
        """
        Initialize the weather API client.

        Args:
            config: External API configuration object
            session: Optional HTTP session, will create default if not provided

        Raises:
            ValueError: If weather API key is not provided
        """
        self.config = config or ExternalAPIConfig()

        if not self.config.weather_api_key:
            raise ValueError("Weather API key is required. Set F1_WEATHER_API_KEY environment variable.")

        self.api_key = self.config.weather_api_key
        self.base_url = self.config.weather_base_url.rstrip('/')

        # Create HTTP client with reasonable defaults
        if session is None:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    'User-Agent': 'F1-Analytics/1.0 (Educational/Weather)',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate'
                },
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            self._own_session = True
        else:
            self.session = session
            self._own_session = False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP session if owned by this client."""
        if self._own_session and self.session:
            await self.session.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the OpenWeatherMap API with retry logic.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            WeatherAPIError: If the request fails after retries
        """
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))

        try:
            # Add API key to all requests
            request_params = params or {}
            request_params['appid'] = self.api_key

            # Default to metric units for consistency
            if 'units' not in request_params:
                request_params['units'] = 'metric'

            logger.debug(f"Making request to Weather API: {url} with params: {request_params}")

            response = await self.session.get(url, params=request_params)
            response.raise_for_status()

            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise WeatherAPIError(f"Invalid JSON response: {str(e)}", response.status_code, None)

            logger.debug(f"Weather API response received: {len(str(data))} characters")
            return data

        except httpx.HTTPStatusError as e:
            # Handle OpenWeatherMap specific errors
            error_msg = f"HTTP error {e.response.status_code}"

            if e.response.status_code == 401:
                error_msg += ": Invalid API key"
            elif e.response.status_code == 404:
                error_msg += ": Location not found"
            elif e.response.status_code == 429:
                error_msg += ": Rate limit exceeded"
            else:
                error_msg += f": {e.response.text}"

            logger.error(f"Weather API HTTP error: {error_msg}")
            raise WeatherAPIError(error_msg, e.response.status_code, None)

        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"Weather API request error: {error_msg}")
            raise WeatherAPIError(error_msg, None, None)

    def _validate_coordinates(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Validate latitude and longitude coordinates.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            Validated (lat, lon) tuple

        Raises:
            ValueError: If coordinates are invalid
        """
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError("Coordinates must be numeric")

        if not (-90 <= lat <= 90):
            raise ValueError(f"Invalid latitude: {lat}. Must be between -90 and 90")

        if not (-180 <= lon <= 180):
            raise ValueError(f"Invalid longitude: {lon}. Must be between -180 and 180")

        return float(lat), float(lon)

    async def get_current_weather(self, lat: float, lon: float, lang: str = 'en') -> Dict[str, Any]:
        """
        Get current weather data for coordinates.

        Args:
            lat: Latitude
            lon: Longitude
            lang: Language code for weather descriptions

        Returns:
            Current weather data

        Raises:
            WeatherAPIError: If the request fails
            ValueError: If coordinates are invalid
        """
        lat, lon = self._validate_coordinates(lat, lon)

        params = {
            'lat': lat,
            'lon': lon,
            'lang': lang
        }

        logger.info(f"Fetching current weather for coordinates ({lat}, {lon})")
        data = await self._make_request('weather', params)
        return data

    async def get_forecast(self, lat: float, lon: float, lang: str = 'en') -> Dict[str, Any]:
        """
        Get 5-day weather forecast for coordinates.

        Args:
            lat: Latitude
            lon: Longitude
            lang: Language code for weather descriptions

        Returns:
            Weather forecast data (5 days, 3-hour intervals)

        Raises:
            WeatherAPIError: If the request fails
            ValueError: If coordinates are invalid
        """
        lat, lon = self._validate_coordinates(lat, lon)

        params = {
            'lat': lat,
            'lon': lon,
            'lang': lang
        }

        logger.info(f"Fetching weather forecast for coordinates ({lat}, {lon})")
        data = await self._make_request('forecast', params)
        return data

    async def get_historical_weather(self, lat: float, lon: float, dt: Union[datetime, date, int]) -> Dict[str, Any]:
        """
        Get historical weather data for a specific date.

        Note: Historical weather data requires a paid OpenWeatherMap subscription.
        This method is included for completeness but may return errors on free tier.

        Args:
            lat: Latitude
            lon: Longitude
            dt: Date/datetime or Unix timestamp

        Returns:
            Historical weather data

        Raises:
            WeatherAPIError: If the request fails or subscription doesn't support historical data
            ValueError: If coordinates or date are invalid
        """
        lat, lon = self._validate_coordinates(lat, lon)

        # Convert date to Unix timestamp
        if isinstance(dt, datetime):
            timestamp = int(dt.timestamp())
        elif isinstance(dt, date):
            timestamp = int(datetime.combine(dt, datetime.min.time()).timestamp())
        elif isinstance(dt, int):
            timestamp = dt
        else:
            raise ValueError(f"Invalid date format: {dt}. Use datetime, date, or Unix timestamp")

        params = {
            'lat': lat,
            'lon': lon,
            'dt': timestamp
        }

        logger.info(f"Fetching historical weather for coordinates ({lat}, {lon}) on {dt}")

        try:
            data = await self._make_request('onecall/timemachine', params)
            return data
        except WeatherAPIError as e:
            if e.status_code == 401:
                raise WeatherAPIError(
                    "Historical weather data requires a paid OpenWeatherMap subscription",
                    e.status_code,
                    e.response_data
                )
            raise

    async def get_weather_for_circuit(self, circuit_id: str, race_date: Union[date, datetime]) -> Dict[str, Any]:
        """
        Get weather data for a specific F1 circuit on a race date.

        This method automatically handles coordinate lookup and provides
        the most relevant weather data based on the race date timing.

        Args:
            circuit_id: F1 circuit identifier (e.g., 'monaco', 'silverstone')
            race_date: Race date

        Returns:
            Weather data with circuit context information

        Raises:
            WeatherAPIError: If the request fails
            ValueError: If circuit_id is unknown or date is invalid
        """
        # Get circuit coordinates
        coordinates = CircuitCoordinates.get_coordinates(circuit_id)
        if not coordinates:
            available_circuits = ', '.join(CircuitCoordinates.get_all_circuits())
            raise ValueError(f"Unknown circuit: {circuit_id}. Available circuits: {available_circuits}")

        lat, lon = coordinates

        # Convert to datetime if needed
        if isinstance(race_date, date) and not isinstance(race_date, datetime):
            # Assume race starts at 2 PM local time (approximate)
            race_datetime = datetime.combine(race_date, datetime.min.time().replace(hour=14))
        else:
            race_datetime = race_date

        now = datetime.now()

        # Determine which API to use based on race date
        if race_datetime.date() == now.date():
            # Race is today - get current weather
            logger.info(f"Getting current weather for {circuit_id} circuit")
            weather_data = await self.get_current_weather(lat, lon)
            data_type = "current"

        elif race_datetime > now:
            # Future race - get forecast
            days_ahead = (race_datetime.date() - now.date()).days
            if days_ahead <= 5:
                logger.info(f"Getting forecast weather for {circuit_id} circuit ({days_ahead} days ahead)")
                weather_data = await self.get_forecast(lat, lon)
                data_type = "forecast"
            else:
                raise WeatherAPIError(f"Weather forecast only available for next 5 days. Race is {days_ahead} days away.")

        else:
            # Historical race - attempt to get historical data
            logger.info(f"Getting historical weather for {circuit_id} circuit")
            try:
                weather_data = await self.get_historical_weather(lat, lon, race_datetime)
                data_type = "historical"
            except WeatherAPIError as e:
                if "subscription" in str(e).lower():
                    # Fallback: return error with helpful message
                    return {
                        "error": "Historical weather data unavailable",
                        "message": "Historical weather requires paid OpenWeatherMap subscription",
                        "circuit_id": circuit_id,
                        "coordinates": {"lat": lat, "lon": lon},
                        "race_date": race_datetime.isoformat(),
                        "fallback_suggestion": "Use cached/historical average for this circuit"
                    }
                raise

        # Add circuit context to response
        result = {
            "circuit_id": circuit_id,
            "coordinates": {"lat": lat, "lon": lon},
            "race_date": race_datetime.isoformat(),
            "data_type": data_type,
            "weather_data": weather_data,
            "timestamp": datetime.now().isoformat()
        }

        return result

    async def get_weather_summary(self, circuit_id: str, race_date: Union[date, datetime]) -> Dict[str, Any]:
        """
        Get a simplified weather summary for a circuit and race date.

        This method extracts key weather information and presents it in a
        standardized format suitable for F1 analytics.

        Args:
            circuit_id: F1 circuit identifier
            race_date: Race date

        Returns:
            Simplified weather summary with key metrics

        Raises:
            WeatherAPIError: If the request fails
            ValueError: If circuit_id is unknown or date is invalid
        """
        weather_data = await self.get_weather_for_circuit(circuit_id, race_date)

        # Handle error case
        if "error" in weather_data:
            return weather_data

        # Extract relevant information based on data type
        data_type = weather_data["data_type"]
        raw_data = weather_data["weather_data"]

        if data_type == "current":
            # Current weather format
            main = raw_data.get("main", {})
            weather = raw_data.get("weather", [{}])[0]
            wind = raw_data.get("wind", {})

            summary = {
                "temperature_celsius": main.get("temp"),
                "feels_like_celsius": main.get("feels_like"),
                "humidity_percent": main.get("humidity"),
                "pressure_hpa": main.get("pressure"),
                "wind_speed_kph": wind.get("speed", 0) * 3.6 if wind.get("speed") else None,  # Convert m/s to km/h
                "wind_direction_degrees": wind.get("deg"),
                "weather_condition": weather.get("main"),
                "weather_description": weather.get("description"),
                "precipitation_mm": raw_data.get("rain", {}).get("1h", 0) + raw_data.get("snow", {}).get("1h", 0)
            }

        elif data_type == "forecast":
            # For forecast, find the closest forecast to race time
            forecasts = raw_data.get("list", [])
            race_timestamp = datetime.fromisoformat(weather_data["race_date"].replace('Z', '+00:00')).timestamp()

            # Find closest forecast
            closest_forecast = None
            min_diff = float('inf')

            for forecast in forecasts:
                forecast_timestamp = forecast.get("dt", 0)
                diff = abs(forecast_timestamp - race_timestamp)
                if diff < min_diff:
                    min_diff = diff
                    closest_forecast = forecast

            if closest_forecast:
                main = closest_forecast.get("main", {})
                weather = closest_forecast.get("weather", [{}])[0]
                wind = closest_forecast.get("wind", {})

                summary = {
                    "temperature_celsius": main.get("temp"),
                    "feels_like_celsius": main.get("feels_like"),
                    "humidity_percent": main.get("humidity"),
                    "pressure_hpa": main.get("pressure"),
                    "wind_speed_kph": wind.get("speed", 0) * 3.6 if wind.get("speed") else None,
                    "wind_direction_degrees": wind.get("deg"),
                    "weather_condition": weather.get("main"),
                    "weather_description": weather.get("description"),
                    "precipitation_mm": closest_forecast.get("rain", {}).get("3h", 0) + closest_forecast.get("snow", {}).get("3h", 0),
                    "forecast_time_diff_hours": min_diff / 3600
                }
            else:
                summary = {"error": "No suitable forecast found"}

        elif data_type == "historical":
            # Historical weather format (OneCall API)
            current = raw_data.get("current", {})
            weather = current.get("weather", [{}])[0]

            summary = {
                "temperature_celsius": current.get("temp"),
                "feels_like_celsius": current.get("feels_like"),
                "humidity_percent": current.get("humidity"),
                "pressure_hpa": current.get("pressure"),
                "wind_speed_kph": current.get("wind_speed", 0) * 3.6 if current.get("wind_speed") else None,
                "wind_direction_degrees": current.get("wind_deg"),
                "weather_condition": weather.get("main"),
                "weather_description": weather.get("description"),
                "precipitation_mm": current.get("rain", {}).get("1h", 0) + current.get("snow", {}).get("1h", 0)
            }

        else:
            summary = {"error": f"Unknown data type: {data_type}"}

        # Add context information
        result = {
            "circuit_id": weather_data["circuit_id"],
            "coordinates": weather_data["coordinates"],
            "race_date": weather_data["race_date"],
            "data_type": data_type,
            "weather_summary": summary,
            "timestamp": datetime.now().isoformat()
        }

        return result

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check against the OpenWeatherMap API.

        Returns:
            Health check result with status and response time
        """
        start_time = datetime.now()

        try:
            # Simple request to check API availability and key validity
            # Use coordinates for London as a test
            data = await self.get_current_weather(51.5074, -0.1278)  # London coordinates
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "api_url": self.base_url,
                "api_key_status": "valid",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            # Determine if it's an API key issue
            api_key_status = "invalid" if "api key" in str(e).lower() or "401" in str(e) else "unknown"

            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_seconds": response_time,
                "api_url": self.base_url,
                "api_key_status": api_key_status,
                "timestamp": datetime.now().isoformat()
            }


# Factory function for easy client creation
async def create_weather_client(config: Optional[ExternalAPIConfig] = None) -> WeatherClient:
    """
    Factory function to create a weather API client.

    Args:
        config: Optional configuration object

    Returns:
        Configured WeatherClient instance

    Raises:
        ValueError: If weather API key is not configured
    """
    return WeatherClient(config)