import json
import ollama

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run_agent(query, checklists):
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

            ai_tools = []
            for tool in avail_tools.tools:
                ai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })

            # Grounding instructions
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an Alexa, a Smart Wardrobe and Travel Outfitter assistant. "
                        "Use MCP tool results as the only source of facts. Do not "
                        "use outside knowledge or infer missing details. For weather "
                        "answers, report only forecast values returned by "
                        "get_weather_forecast. Do not describe conditions such as "
                        "'calm winds', 'mild evenings', or 'sunny' unless the tool "
                        "explicitly returns them. For wardrobe and packing answers, "
                        "copy clothing item names exactly as returned by the relevant "
                        "tool. Never replace 'default' with examples such as 'light "
                        "layers' or 'breathable fabrics'. Do not add clothing, weather "
                        "descriptions, tips, assumptions, or explanations that are "
                        "not in the tool result. Include every date returned by the "
                        "packing checklist, including dates whose clothing is "
                        "'default'. If a value is missing, say it was not provided "
                        "rather than guessing. Interpret precipitation probability "
                        "as the chance of precipitation, not as proof that rain will "
                        "occur. Say rain is expected when the reported probability is "
                        "70% or higher; below 70%, say rain is not expected and state "
                        "the probability. Do not say rain is expected merely because "
                        "a probability value is present. Keep the response concise "
                        "and organize recommendations by date."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ]

            response = ollama.chat(
                model="qwen3:8b",
                messages=messages,
                tools=ai_tools if ai_tools else None
            )

            assistant_message = response["message"]
            messages.append(assistant_message)

            if (
                "tool_calls" in assistant_message
                and assistant_message["tool_calls"]
            ):
                for tool in assistant_message["tool_calls"]:
                    tool_name = tool["function"]["name"]
                    tool_args = tool["function"]["arguments"]

                    print(
                        f"AI selected tool-{tool_name} "
                        f"arguments-{tool_args}"
                    )

                    server_result = await session.call_tool(
                        tool_name,
                        arguments=tool_args
                    )

                    if server_result.isError:
                        error_details = "\n".join(
                            item.text
                            for item in server_result.content
                            if hasattr(item, "text")
                        )
                        return f"Tool {tool_name} failed: : {error_details}"

                    text_parts = [
                        item.text
                        for item in server_result.content
                        if hasattr(item, "text")
                    ]

                    if not text_parts:
                        print(f"Tool {tool_name} returned no text.")
                        return

                    try:
                        result_parts = [
                            json.loads(text)
                            for text in text_parts
                        ]
                    except json.JSONDecodeError as exc:
                        print(
                            f"Invalid JSON returned by {tool_name}: {exc}"
                        )
                        return

                    result = (
                        result_parts[0]
                        if len(result_parts) == 1
                        else result_parts
                    )

                    if tool_name == "generate_packing_checklist":
                        if (
                            isinstance(result, dict)
                            and "Date" in result
                            and "Clothing" in result
                        ):
                            result = [result]

                        if not isinstance(result, list) or not all(
                            isinstance(item, dict)
                            and "Date" in item
                            and "Clothing" in item
                            for item in result
                        ):
                            return "Unexpected packing checklist format."

                        checklists.extend(result)

                    elif tool_name == "analyze_wardrobe_suitability":
                        wardrobe_data = result

                        if (
                            isinstance(wardrobe_data, list)
                            and len(wardrobe_data) == 1
                            and isinstance(wardrobe_data[0], dict)
                        ):
                            wardrobe_data = wardrobe_data[0]

                            checklist = []

                            for clothing in wardrobe_data:
                                checklist.append((clothing["Date"], clothing["Clothing"]))

                        if (
                            not isinstance(wardrobe_data, dict)
                            or not isinstance(
                                wardrobe_data.get("final_recommendations"),
                                list
                            )
                        ):
                            print(
                                "Unexpected wardrobe recommendation format."
                            )
                            return "Unexpected wardrobe recommendation format."

                        recommendations = wardrobe_data[
                            "final_recommendations"
                        ]
                        if not all(
                            isinstance(item, dict)
                            and "date" in item
                            and "cloths" in item
                            for item in recommendations
                        ):
                            return "Unexpected wardrobe recommendation format."

                        checklists.extend(
                            {
                                "Date": item["date"],
                                "Clothing": item["cloths"],
                            }
                            for item in recommendations
                        )

                    # Send the tool result back to Ollama
                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(result)
                    })

                # Other tools, such as weather and forecast,
                # still use Ollama to generate a concise response.
                final_response = ollama.chat(
                    model="qwen3:8b",
                    messages=messages
                )

                return "AI response:\n" + final_response["message"]["content"]
            else:
                return "Model answer (no tool call):\n" + assistant_message["content"]
        
