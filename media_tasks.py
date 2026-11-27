"""Read an existing Ace Data Cloud media task and format its public URLs."""
import http.client
import json
from urllib.parse import quote, urlsplit


# Service key, display name, output kind and the output field for each API.
SERVICES = {
    'acemusic': ('ACE Music', 'audio', 'audio_url'),
    'suno': ('Suno', 'audio', 'audio_url'),
    'nano-banana': ('Nano Banana', 'image', 'image_url'),
    'openai': ('GPT Image', 'image', 'url'),
    'seedream': ('Seedream', 'image', 'image_url'),
    'flux': ('FLUX', 'image', 'image_url'),
    'seedance': ('Seedance', 'video', 'video_url'),
    'kling': ('Kling', 'video', 'video_url'),
    'veo': ('Veo', 'video', 'video_url'),
    'hailuo': ('Hailuo', 'video', 'video_url'),
}


def retrieve(service, task_id, token):
    if service not in SERVICES:
        raise ValueError('Choose a supported media service.')
    connection = http.client.HTTPSConnection('api.acedata.cloud', timeout=25)
    try:
        connection.request('POST', '/' + service + '/tasks',
                           json.dumps({'action': 'retrieve', 'id': task_id}),
                           {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError('The service returned HTTP {}.'.format(response.status))
        return json.load(response)
    finally:
        connection.close()


def media_links(service, task_id, record):
    if not isinstance(record, dict) or record.get('id') != task_id:
        raise ValueError('Could not find that task under this service and application.')
    result = record.get('response') or {}
    if not isinstance(result, dict) or result.get('task_id', task_id) != task_id:
        raise ValueError('The returned task did not match the requested ID.')
    data = result.get('data')
    if service == 'seedance':
        rows = [data.get('content')] if isinstance(data, dict) else []
    elif service == 'kling':
        rows = [result]
    else:
        rows = data if isinstance(data, list) else []
    field = SERVICES[service][2]
    links = []
    for row in rows:
        url = row.get(field) if isinstance(row, dict) else None
        if not isinstance(url, str) or any(c in url for c in '\r\n\t'):
            continue
        try:
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                continue
        except ValueError:
            continue
        if url not in links:
            links.append(url)
    if not links:
        raise ValueError('This task has no public asset URL yet. Check its status in your service account.')
    return links


def markdown(service, index, url):
    name, kind, _ = SERVICES[service]
    label = '{} {} {}'.format(name, kind, index + 1)
    value = quote(url, safe=":/?#[]@!$&'*+,;=%~")
    return '{}[{}](<{}>)'.format('!' if kind == 'image' else '', label, value)
