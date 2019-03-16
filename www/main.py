import json
import logging
import os
import sys

import requests
from flask import Flask, request, Response
from google.cloud import tasks

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOG = logging.getLogger('www:main')

app = Flask(__name__)


def get_project_location():
    loc = os.getenv('PROJECT_LOCATION')
    if not loc:
        loc = requests.get('http://metadata.google.internal/computeMetadata/v1/instance/zone',
                           headers={'Metadata-Flavor': 'Google'}).text
        loc = loc.split('/')[-1]
        if loc.count('-') > 1:
            loc = loc[:loc.rindex('-')]
        os.environ['PROJECT_LOCATION'] = loc
    return loc


project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
project_location = get_project_location()
task_queue = os.getenv('TASK_QUEUE_NAME') or 'default'
tg_bot_token = os.getenv('TG_BOT_TOKEN')
app_base_url = f'https://{project_id}.appspot.com'
tg_api_base_url = 'https://api.telegram.org/bot'
tg_api_url = f'{tg_api_base_url}{tg_bot_token}'
wh_url = f'{app_base_url}/telegram/update/{tg_bot_token}'

tasks_client = tasks.CloudTasksClient()
task_parent = tasks_client.queue_path(project_id, project_location, task_queue)


def telegram_request(command: str, method: str = 'post', data: dict = None) -> dict:
    url = f'{tg_api_url}/{command}'
    response = requests.request(method=method.lower(), url=url, data=data)
    res = response.json()
    if res['ok']:
        return res['result']
    raise requests.exceptions.BaseHTTPError(f'Error requesting Telegram API: {res}')


@app.route('/')
def hello():
    return 'Zhazha here!'


@app.route('/webhook')
def webhook():
    LOG.info('Validating Telegram webhook...')
    allowed_updates = [
        "message",
        "inline_query",
        "chosen_inline_result",
        "callback_query",
        "pre_checkout_query"
    ]
    try:
        wh_info = telegram_request('getWebhookInfo')
        LOG.debug(f'Current webhook info: {wh_info}')
        if wh_info['url'] != wh_url \
                or wh_info.get('allowed_updates', []) != allowed_updates:
            LOG.debug(f'Updating webhook, set url={wh_url}, allowed_updates={allowed_updates}')
            telegram_request('setWebhook', data={'url': wh_url, 'allowed_updates': json.dumps(allowed_updates)})
    except Exception as e:
        LOG.error(str(e))
        return 'Error setting Telegram webhook'
    else:
        LOG.info('Webhook is set up.')
        return 'Telegram webhook is set'


@app.route(f'/telegram/update/{tg_bot_token}', methods=['POST'])
def telegram_update():
    try:
        update = request.get_json()
        LOG.debug(f'Update received: {update}')

        payload = json.dumps(update, ensure_ascii=False).encode()

        task = {
            'app_engine_http_request': {
                'http_method': 'POST',
                'relative_uri': '/update',
                'app_engine_routing': {
                    'service': 'telegram'
                },
                'body': payload
            }
        }

        response = tasks_client.create_task(task_parent, task)
        LOG.debug(f'Created task {response.name}: {task}')
    except Exception as e:
        LOG.error(str(e))
    finally:
        return Response(status=200)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
