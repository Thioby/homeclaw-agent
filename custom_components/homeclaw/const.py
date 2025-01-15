"""Constants for the Homeclaw integration."""

DOMAIN = "homeclaw"
CONF_API_KEY = "api_key"
CONF_WEATHER_ENTITY = "weather_entity"

# AI Provider configuration keys
CONF_LLAMA_TOKEN = "llama_token"  # nosec B105
CONF_OPENAI_TOKEN = "openai_token"  # nosec B105
CONF_GEMINI_TOKEN = "gemini_token"  # nosec B105
CONF_OPENROUTER_TOKEN = "openrouter_token"  # nosec B105
CONF_ANTHROPIC_TOKEN = "anthropic_token"  # nosec B105
CONF_ALTER_TOKEN = "alter_token"  # nosec B105
CONF_ZAI_TOKEN = "zai_token"  # nosec B105
CONF_LOCAL_URL = "local_url"
CONF_LOCAL_MODEL = "local_model"

# Available AI providers
AI_PROVIDERS = [
    "llama",
    "openai",
    "gemini",
    "gemini_oauth",
    "openrouter",
    "anthropic",
    "anthropic_oauth",
    "alter",
    "zai",
    "local",
]

# Valid providers for WebSocket API validation
VALID_PROVIDERS = frozenset(AI_PROVIDERS)

# AI Provider constants
CONF_MODELS = "models"

# Supported AI providers
DEFAULT_AI_PROVIDER = "openai"

# Anthropic OAuth
CONF_ANTHROPIC_OAUTH = "anthropic_oauth"
ANTHROPIC_OAUTH_PROVIDER = "anthropic_oauth"

# Gemini OAuth
CONF_GEMINI_OAUTH = "gemini_oauth"
GEMINI_OAUTH_PROVIDER = "gemini_oauth"

# RAG (Retrieval-Augmented Generation) configuration
CONF_RAG_ENABLED = "rag_enabled"
DEFAULT_RAG_ENABLED = False  # Disabled by default for safety
