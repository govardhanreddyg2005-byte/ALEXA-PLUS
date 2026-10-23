import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    url = "http://localhost:8000/mcp"

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Discover available tools
            avail_tools = await session.list_tools()

            for tool in avail_tools.tools:
                print(f"Tool: {tool.name} - {tool.description}")

            weather_tool = await session.call_tool(
                "get_weather",
                arguments={
                    "city": "Tokyo"
                    }
            )

            forecast_tool = await session.call_tool(
                "get_weather_forecast",
                arguments={
                    "city": "Sapporo",
                    "days": 7
                }
            )

            wardrobe_tool = await session.call_tool(
                    "analyze_wardrobe_suitability",
                    arguments={
                        "city" : "Sapporo",
                        "days": 7
                    }
                )

            packing_tool = await session.call_tool(
                "generate_packing_checklist",
                arguments={
                    "city" : "Sapporo",
                    "days": 7
                }
            )

            try:

                data = weather_tool.content[0].text

                load_data = json.loads(data)
                forecast = [json.loads(item.text) for item in forecast_tool.content]
                wardrobe_data = json.loads(wardrobe_tool.content[0].text)
                checklists = [json.loads(item.text) for item in packing_tool.content]
            except Exception as e:
                print("Error: ", e)

            else:
                print("Temperature:", load_data["temperature"],"°C")
                print("Windspeed:", load_data["windspeed"],"km/h")
                        
                for item in forecast:
                    print("date:", item["date"])
                    print("Max Temp:", item["max_temp"],"°C")
                    print("Min Temp:", item["min_temp"], "°C")
                    print("Precipitation Probability: ",item["precipitation_probability"],"%")
                    print("Wind Speed:", item["wind_speed"],"km/h")
                    print("Snow Fall:", item["snowfall_sum"])
                    print()

                print("Rain recommendations:")
                for day in wardrobe_data["rain_recommendations"]:
                    print("Date:", day["date"])
                    print("Precipitation Probability:",day["precipitation_probability"],"%")
                    print("Level:", day["level"])
                    print("Clothing:", day["cloths"])
                    print()

                print("Snowfall recommendations:")
                for day in wardrobe_data["snowfall_recommendations"]:
                    print("Date:", day["date"])
                    print("Snowfall:", day["snowfall_sum"])
                    print("Level:", day["level"])
                    print("Clothing:", day["cloths"])
                    print()

                print("Temperature recommendations:")
                for day in wardrobe_data["temperature_recommendations"]:
                    print("Date:", day["date"])
                    print("Minimum temperature:", day["min_temp"], "°C")
                    print("Maximum temperature:", day["max_temp"], "°C")
                    print("Level:", day["level"])
                    print("Clothing:", day["cloths"])
                    print()

                print("Wind recommendations:")
                for day in wardrobe_data["wind_recommendations"]:
                    print("Date:", day["date"])
                    print("Wind speed:", day["wind_speed"], "km/h")
                    print("Level:", day["level"])
                    print("Clothing:", day["cloths"])
                    print()

                print("Final recommendations:")
                for day in wardrobe_data["final_recommendations"]:
                    print("Date:", day["date"])
                    print("weather event:", day["weather_event"])
                    print("Clothing:", day["cloths"])
                    print()

            print("Final Checklist:")
            for checklist in checklists:
                print("Date:", checklist["Date"])
                print("Clothing:", checklist["Clothing"])
                print()

if __name__ == "__main__":
    asyncio.run(main())