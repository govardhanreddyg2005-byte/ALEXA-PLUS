# Alexa+ Weather & Packing Assistant

Alexa+ is a chat-based weather and travel outfitter. Ask about current weather, upcoming forecasts, clothing for forecast conditions, or what to pack for a trip. The assistant uses live weather data and presents clothing recommendations by date.

## Features

* Get current weather and multi-day forecasts for a city.
* Get date-specific clothing recommendations based on rain, snow, temperature, and wind.
* Generate a packing checklist and select clothing items for each date.
* Ask questions through a Streamlit chat interface and review conversation history.
* Hear each new assistant response spoken aloud using offline text-to-speech. This is speech output only; queries are entered as text.

## Architecture

1. `app.py` renders the Streamlit chat, sends submitted questions to the AI client, displays clothing selections from tool results, and speaks new responses.
2. `mcp_host/aiclient.py` connects to the MCP server, exposes its tools to the local Ollama model, and returns the model's response.
3. `server/server.py` hosts the MCP weather, wardrobe, and packing tools.
4. The MCP tools request geocoding and weather forecast data from the public Open-Meteo APIs.
5. `client/client.py` is a console example for calling the MCP tools directly.

## Technologies

* **Python** — application and tool implementation.
* **Streamlit** — chat interface.
* **Ollama** — runs the local `qwen3:8b` model and selects MCP tools.
* **MCP (Model Context Protocol)** — connects the AI client to the weather and wardrobe tools.
* **Open-Meteo** — geocoding and weather forecast data.
* **pyttsx3** — offline text-to-speech library for converting assistant responses into spoken audio using an installed system voice.
* **Requests** — HTTP requests to Open-Meteo.

## Prerequisites

* Python 3.10 or newer.
* Ollama installed and running.
* The `qwen3:8b` model downloaded in Ollama.
* Internet access for Open-Meteo weather requests.
* An operating-system speech voice supported by `pyttsx3` for spoken responses.

## Installation

From the project directory, create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell does not allow script activation, use the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install [Ollama](https://ollama.com/) if it is not already installed, then download the model:

```powershell
ollama pull qwen3:8b
```

## Configuration

No project environment variables or API keys are required. Open-Meteo is accessed directly by the weather server. Keep any local credentials or environment-specific settings out of source control.

## Running the Project

Open two PowerShell terminals in the project directory.

**Terminal 1 — Start the MCP server:**

```powershell
.\.venv\Scripts\python.exe server\server.py
```

The MCP server should listen at `http://localhost:8000/mcp`.

Ensure Ollama is running and the `qwen3:8b` model is available.

**Terminal 2 — Start the Streamlit app:**

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit in your browser. Enter a question in the chat input; answers are displayed in the conversation and spoken aloud through the machine's configured speech voice.

## Source Files

* `app.py` — Streamlit application and speech output.
* `mcp_host/aiclient.py` — Ollama and MCP client integration.
* `server/server.py` — MCP weather, wardrobe, and packing tools.
* `client/client.py` — console example MCP client.
* `requirements.txt` — pinned Python dependencies.

No separate project assets are needed to run the application.

## License

MIT License.
