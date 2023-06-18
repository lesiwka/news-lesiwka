import re
from concurrent import futures


def validate(text):
    return re.search("[ґєіїҐЄІЇ]", text) or not re.search("[ёўъыэЁЎЪЫЭ]", text)


def time_limit(timeout, func, *args, **kwargs):
    with futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(func, *args, **kwargs).result(timeout)
