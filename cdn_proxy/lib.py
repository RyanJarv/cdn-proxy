class CdnProxyException(Exception):
    pass


def trim(s: str, length: int):
    if len(s) <= length:
        return s
    else:
        return s[0:length] + '...'
