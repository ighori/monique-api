### The configuration of the Monique API app. The configuration can be
### overriden by putting a subset of config variables in apiconfig_override.py file
### (which must be in PYTHONPATH).


from mqe.util import setup_logging


# The base URL under which the API application is available
BASE_URL_API = 'http://localhost:8101'


# Flask settings

class FlaskSettings(object):
    JSON_AS_ASCII = False


# The logging level of messages outputted to stdout. Setting NONE disables
# configuring the logging.
LOGGING_LEVEL = 'INFO'


# Data sizes limits

# The default number of returned items (like report instances)
DEFAULT_GET_LIMIT = 20

# The maximal number of returned items (for more items, paging is used)
MAX_GET_LIMIT = 100

# The limits of lengths of fields like tag values or report names
SIMPLE_VALUE_LEN_LIMIT = 200

# The limit of lengths of data sizes supplied by users, like custom metadata
USER_VALUE_LEN_LIMIT = 5000


# Monique API uses UserDAO from Monique Web
DAO_MODULES = [
    ('cassandra', 'mqeweb.dao.cassandradb.cassandradao'),
    ('sqlite3', 'mqeweb.dao.sqlite3db.sqlite3dao'),
]

try:
    import apiconfig_override
    reload(apiconfig_override)
    from apiconfig_override import *
except ImportError:
    pass
