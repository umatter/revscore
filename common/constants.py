MODEL_PATH_ENV_VAR = "MODEL_PATH"
MODEL_PATH_FOR_DRAFT_QUALITY_MODEL_TYPE = "/mnt/models/model.bz2"
DEFAULT_MODEL_PATH = "/mnt/models/model.bin"
WIKI_URL_ENV_VAR = "WIKI_URL"

WIKI_URL_NOT_FOUND_IN_ENV_ERR = f"The environment variable {WIKI_URL_ENV_VAR} is not set. Please set it before running the server."

API_USER_AGENT = "revscoring demo"

FEATURE_VAL_KEY = "feature_values"
EXTENDED_OUTPUT_KEY = "extended_output"
EVENT_KEY = "event"
EVENTGATE_URL = "EVENTGATE_URL"
EVENTGATE_STREAM = "EVENTGATE_STREAM"
AIOHTTP_CLIENT_TIMEOUT = "AIOHTTP_CLIENT_TIMEOUT"
TLS_CERT_BUNDLE_PATH = "/etc/ssl/certs/wmf-ca-certificates.crt"
WIKI_HOST_ENV_VAR = "WIKI_HOST"
MISSING_REV_ID_ERR = "Missing 'rev_id' in input data."
INVALID_REV_ID_ERR = "Expected 'rev_id' to be an integer."