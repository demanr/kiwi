# kiwi

HTN 2025, making your clipboard a supertool

## Setup

### Environment Variables

The following environment variables are required:

- `GROQ_API_KEY`: Your Groq API key (required if using Groq provider)
- `GEMINI_API_KEY`: Your Google Gemini API key (required if using Gemini provider)
- `MODEL_PROVIDER`: Choose the AI provider (`groq` or `gemini`, defaults to `groq`)

### Model Provider Configuration

You can switch between different AI providers by setting the `MODEL_PROVIDER` environment variable:

```bash
# Use Groq (default)
export MODEL_PROVIDER=groq
export GROQ_API_KEY=your_groq_api_key

# Use Google Gemini
export MODEL_PROVIDER=gemini
export GEMINI_API_KEY=your_gemini_api_key
```

### Installation

1. Install dependencies:

```bash
pip install -r app/requirements.txt
```

2. Set up your environment variables in a `.env` file or export them directly
3. Run the application:

```bash
cd app
python main.py
```

### Supported Models

- **Groq**: `llama-3.3-70b-versatile` (default Groq model)
- **Gemini**: `gemini-2.5-flash-lite` (optimized for cost efficiency and low latency)

### Google Search Integration

When using Gemini as the provider, the application automatically enhances responses with real-time web search when queries contain keywords like:

- "current", "recent", "latest", "news", "today", "now", "update"

This provides access to the most current information beyond the model's training cutoff date.

The application will automatically fall back to Groq if Gemini initialization fails.
