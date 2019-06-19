import json
import logging
import os
import sys

import requests
from flask import Flask, request, Response

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOG = logging.getLogger('telegram:main')

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
tg_bot_token = os.getenv('TG_BOT_TOKEN')
tg_api_base_url = 'https://api.telegram.org/bot'
tg_api_url = f'{tg_api_base_url}{tg_bot_token}'
markov_service_url = f'http://markov.{project_id}.appspot.com'

app = Flask(__name__)


def telegram_request(command: str, method: str = 'post', data: dict = None) -> dict:
    url = f'{tg_api_url}/{command}'
    response = requests.request(method=method.lower(), url=url, json=data)
    res = response.json()
    if res['ok']:
        return res['result']
    raise requests.exceptions.BaseHTTPError(f'Error requesting Telegram API: {res}')


@app.route('/update', methods=['POST'])
def handle_update():
    try:
        update = json.loads(request.get_data(as_text=True))
        if 'message' in update:
            process_message(update['message'])
    except Exception as e:
        LOG.error(str(e))
    finally:
        return Response(status=200)


def process_message(message: dict):
    chat_id: int = message['chat']['id']
    text: str = message.get('text', None)
    entities = message.get('entities', None)
    if not text:
        text = message.get('caption', None)
        entities = message.get('caption_entities', None)
    if not text:
        return
    if entities:
        text = _strip_entities(text, entities)
    text = text.strip().lower()
    if not text:
        return

    if text.startswith('жажа обосри') or text.startswith('жажа унизь'):
        # go obsirat
        target = None
        text = text.replace('жажа обосри', '').replace('жажа унизь', '').strip()
        if text:
            target = text.split()[0]
        obosri(chat_id, start=target)
    else:
        # save new tokens
        save(chat_id, text)


def obosri(chat_id, start=None):
    payload = {'dictionary': chat_id}
    if start:
        payload['start'] = start
    res = requests.post(f'{markov_service_url}/gen',
                        json=payload).json()
    if res['ok']:
        telegram_request('sendMessage', data={
            'chat_id': chat_id,
            'text': res['text']
        })
    else:
        LOG.error(res['error'])


def save(chat_id, text: str):
    payload = {
        'dictionary': chat_id,
        'corpus': text
    }
    res = requests.post(f'{markov_service_url}/train',
                        json=payload).json()
    if not res['ok']:
        LOG.error(res['error'])


def _strip_entities(text, entities):
    starts = [0]
    ends = []
    for e in entities:
        starts.append(e['offset'] + e['length'])
        ends.append(e['offset'])
    ends.append(len(text))
    result = []
    for start, end in zip(starts, ends):
        result.append(text[start:end])
    return ''.join(result)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
