from typing import Any
import time

from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Alexa Assistant")
url = "https://api.open-meteo.com/v1/forecast?latitude=13.08784&longitude=80.27847&current_weather=true"

@mcp.tool()
def get_weather(city: str) -> dict[str, Any]:
    """Fetch current weather conditions for a city using Open-Meteo.

    Args:
        city: City or place name to search for, such as "Chennai".

    Returns:
        The Open-Meteo current-weather object, typically containing time,
        temperature in Celsius, windspeed in km/h, winddirection in degrees,
        and weathercode.
    """

    geocode_api = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"

    geo_response = requests.get(
        geocode_api,
        params = {
            "name" : city,
            "count" : 1
        }
    )

    geo_data = geo_response.json()

    coordinates = geo_data["results"][0]

    latitude = coordinates["latitude"]

    longitude = coordinates["longitude"]

    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"

    get_data = requests.get(url)

    weather_data = get_data.json()

    current = weather_data["current_weather"]

    return current


@mcp.tool()
def get_weather_forecast(city: str, days: int) -> list[dict[str, Any]]:
    """Fetch a daily weather forecast for a city from Open-Meteo.

    Args:
        city: City or place name to geocode, such as "Chennai".
        days: Number of daily forecast days to request.

    Returns:
        One dictionary per day with keys date, max_temp and min_temp (°C),
        precipitation_probability (percent), wind_speed (km/h), and
        snowfall_sum (cm). Raises an error if geocoding or the forecast
        request fails, no city result is found, or the API response is invalid.
    """

    # STEP 1: Convert the city name into coordinates.
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"

    try:
        geo_response = requests.get(
            geocode_url,
            params={"name": city, "count": 1},
            timeout=20
        )

        print("GEOCODING STATUS:", geo_response.status_code, flush=True)

        geo_response.raise_for_status()
        geo_data = geo_response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Geocoding request failed for {city!r}: {exc}"
        ) from exc

    results = geo_data.get("results")

    if not results:
        raise ValueError(
            f"No coordinates found for city {city!r}. "
            f"API response: {geo_data}"
        )

    coordinates = results[0]
    latitude = coordinates["latitude"]
    longitude = coordinates["longitude"]

    print(
        f"CITY: {city!r}, LATITUDE: {latitude}, LONGITUDE: {longitude}",
        flush=True
    )

    # STEP 2: Request the daily forecast.
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max,"
            "wind_speed_10m_max,"
            "snowfall_sum"
        ),
        "forecast_days": days,
        "timezone": "auto"
    }

    data = None

    for attempt in range(3):
        try:
            api_response = requests.get(
                forecast_url,
                params=params,
                timeout=(5, 30)
            )

            print("REQUEST URL:", api_response.url, flush=True)
            print("STATUS CODE:", api_response.status_code, flush=True)
            print("RAW RESPONSE:", api_response.text[:2000], flush=True)

            api_response.raise_for_status()
            data = api_response.json()

            break

        except requests.Timeout as exc:
            print(
                f"Forecast request timed out "
                f"(attempt {attempt + 1}/3).",
                flush=True
            )

            if attempt == 2:
                raise RuntimeError(
                    "Open-Meteo forecast request timed out after 3 attempts."
                ) from exc

            time.sleep(attempt + 1)

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Forecast HTTP request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                f"Forecast response was not valid JSON. "
                f"Response: {api_response.text[:1000]}"
            ) from exc

    if data is None:
        raise RuntimeError("Unable to obtain a forecast.")

    if data.get("error"):
        raise RuntimeError(
            f"Open-Meteo API error: {data.get('reason', data)}"
        )

    daily = data.get("daily")

    if not isinstance(daily, dict):
        raise RuntimeError(
            f"Forecast response has no daily dictionary. "
            f"Available keys: {list(data.keys())}"
        )

    # STEP 5: Build one dictionary for each forecast day.
    forecasts = []

    for date, max_temp, min_temp, precipitation_probability, wind_speed, snowfall in zip(
        daily["time"],
        daily["temperature_2m_max"],
        daily["temperature_2m_min"],
        daily["precipitation_probability_max"],
        daily["wind_speed_10m_max"],
        daily["snowfall_sum"]
    ):
        forecasts.append({
            "date": date,
            "max_temp": max_temp,
            "min_temp": min_temp,
            "precipitation_probability": precipitation_probability,
            "wind_speed": wind_speed,
            "snowfall_sum": snowfall
        })

    return forecasts

@mcp.tool()
def analyze_wardrobe_suitability(
    city: str, days: int
) -> dict[str, Any]:
    """Recommend clothing for rain, snow, temperature, and wind by forecast day.

    Args:
        city: City or place name to analyze, such as "Chennai".
        days: Number of forecast days to analyze.

    Returns:
        A dictionary containing rain_recommendations,
        snowfall_recommendations, temperature_recommendations,
        wind_recommendations, and final_recommendations. Rain levels are low
        through 20%, moderate above 20% through 50%, high above 50% through
        100%, unknown when probability is missing, and unclassified outside
        that range. Snow is high when snowfall is greater than zero. Cold
        means minimum temperature at or below 10 °C; hot means maximum
        temperature at or above 30 °C; windy means maximum wind speed at or
        above 30 km/h. Final entries combine detected event labels in
        weather_event and provide deduplicated clothing in cloths. Snowfall
        takes precedence over the rain event label when both are present.
    """

    forecast = get_weather_forecast(city, days)

    clothing_inventory = {
        "rain": [
            "raincoat", "umbrella", "cap", "waterproof boots"
        ],

        "snow": [
            "insulated winter coat", "thermal layers", "waterproof insulated boots",
            "gloves", "warm hat", "scarf"
        ],

        "cold": [
            "warm coat", "thermal layers", "gloves", "warm hat"
        ],

        "heat": [
            "lightweight breathable clothing", "wide-brimmed hat", "sunglasses"
        ],

        "wind": [
            "windbreaker", "secure closed-toe shoes"
        ]
    }

    daily_recommendations = []
    snowfall_recommendations = []
    temperature_recommendations = []
    wind_recommendations = []

    for day in forecast:
        if day["precipitation_probability"] is None:
            level = "unknown"
            clothes = "default"
        elif day["precipitation_probability"] <= 20:
            level = "low"
            clothes = "default"
        elif day["precipitation_probability"] <= 50:
            level = "moderate"
            clothes = "use default"
        elif day["precipitation_probability"] <= 100:
            level = "high"
            clothes = clothing_inventory["rain"]
        else:
            level = "unclassified"
            clothes = "default"

        daily_recommendations.append({
            "date": day["date"],
            "precipitation_probability": day["precipitation_probability"],
            "level": level,
            "cloths": clothes
        })

        if day["snowfall_sum"] is None:
            level = "unknown"
            clothes = "default"
        elif day["snowfall_sum"] == 0:
            level = "low"
            clothes = "default"
        elif day["snowfall_sum"] > 0:
            level = "high"
            clothes = clothing_inventory["snow"]
        else:
            level = "unclassified"
            clothes = "default"

        snowfall_recommendations.append({
            "date": day["date"],
            "snowfall_sum": day["snowfall_sum"],
            "level": level,
            "cloths": clothes
        })

        if day["min_temp"] is not None and day["min_temp"] <= 10:
            temperature_level = "cold"
            temperature_clothes = clothing_inventory["cold"]
        elif day["max_temp"] is not None and day["max_temp"] >= 30:
            temperature_level = "hot"
            temperature_clothes = clothing_inventory["heat"]
        else:
            temperature_level = "comfortable"
            temperature_clothes = "default"

        temperature_recommendations.append({
            "date": day["date"],
            "min_temp": day["min_temp"],
            "max_temp": day["max_temp"],
            "level": temperature_level,
            "cloths": temperature_clothes,
        })

        if day["wind_speed"] is not None and day["wind_speed"] >= 30:
            wind_level = "windy"
            wind_clothes = clothing_inventory["wind"]
        else:
            wind_level = "calm"
            wind_clothes = "default"

        wind_recommendations.append({
            "date": day["date"],
            "wind_speed": day["wind_speed"],
            "level": wind_level,
            "cloths": wind_clothes,
        })
    
    recommendations = {
        "rain_recommendations": daily_recommendations,
        "snowfall_recommendations": snowfall_recommendations,
        "temperature_recommendations": temperature_recommendations,
        "wind_recommendations": wind_recommendations,
    }

    final_recommendations = []

    for rainy, snowfall, temperature, wind in zip(
        recommendations["rain_recommendations"],
        recommendations["snowfall_recommendations"],
        recommendations["temperature_recommendations"],
        recommendations["wind_recommendations"],
    ):
        clothing = []
        weather_events = []

        if snowfall["snowfall_sum"] is not None and snowfall["snowfall_sum"] > 0:
            clothing.extend(snowfall["cloths"])
            weather_events.append("Snowfall")
        elif rainy["precipitation_probability"] is not None and rainy["precipitation_probability"] > 50:
            clothing.extend(rainy["cloths"])
            weather_events.append("Rain likely")

        if temperature["level"] == "cold":
            clothing.extend(temperature["cloths"])
            weather_events.append("Cold")
        elif temperature["level"] == "hot":
            clothing.extend(temperature["cloths"])
            weather_events.append("Hot")

        if wind["level"] == "windy":
            clothing.extend(wind["cloths"])
            weather_events.append("Windy")

        if not clothing:
            clothing = ["default"]
        if not weather_events:
            weather_events.append("No significant conditions")

        final_recommendations.append({
            "date": rainy["date"],
            "weather_event": ", ".join(weather_events),
            "cloths": list(dict.fromkeys(clothing)),
        })

    return {
        "rain_recommendations": daily_recommendations,
        "snowfall_recommendations": snowfall_recommendations,
        "temperature_recommendations": temperature_recommendations,
        "wind_recommendations": wind_recommendations,
        "final_recommendations": final_recommendations,
    }


@mcp.tool()
def generate_packing_checklist(
    city: str, days: int
) -> list[dict[str, Any]]:
    """Build a deduplicated packing checklist from wardrobe recommendations.

    Args:
        city: City or place name to create a checklist for.
        days: Number of forecast days to include.

    Returns:
        A list of items with Date and Clothing keys. Clothing is copied from
        each day's final wardrobe recommendation. Entries are included when
        weather_event contains Cold, Hot, Windy, Rain likely, or
        No significant conditions.
    """

    wardrobe = analyze_wardrobe_suitability(city, days)

    checklist = []

    for final in wardrobe["final_recommendations"]:
        events = [event.strip() for event in final["weather_event"].split(",")]

        if any(event in events for event in (
            "Cold",
            "Hot",
            "Windy",
            "Rain likely",
            "No significant conditions",
        )):
            checklist.append({
                "Date": final["date"],
                "Clothing": final["cloths"]
            })

    unique_checklist = dict.fromkeys(
        (item["Date"], tuple(item["Clothing"])) for item in checklist
    )

    checklists = [
        {"Date": key, "Clothing": list(value)}
        for key, value in unique_checklist
    ]

    return checklists
    
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
