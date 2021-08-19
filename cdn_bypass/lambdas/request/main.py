import random
import os


def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    headers = request['headers']

    host = os.getenv('HOST')
    if not host:
        raise UserWarning('The environment variable HOST is not set.')

    forwarded_for = os.getenv('X_FORWARDED_FOR')
    if not forwarded_for:
        # Set randomly
        pass

    headers['host'] = [{
        "key": "Host",
        "value": host,
    }]

    headers['x-forwarded-for'] = [{
        "key": "X-Forwarded-For",
        "value": forwarded_for,
    }]

    return request