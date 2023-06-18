import os

if os.getenv("SERVER_SOFTWARE"):
    from . import memcache as cache
else:
    from . import tmpcache as cache
