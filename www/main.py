import json
import logging
import os
import sys
import time

import requests
from flask import Flask, request, Response

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOG = logging.getLogger('www:main')

app = Flask(__name__)
app_base_url = os.getenv('APP_BASE_URL')
tg_bot_token = os.getenv('TG_BOT_TOKEN')
tg_api_base_url = 'https://api.telegram.org/bot'
tg_api_url = f'{tg_api_base_url}{tg_bot_token}'
tg_service_url = 'http://telegram:8080'

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
        wh_url = f'{app_base_url}/telegram/update/{tg_bot_token}'
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
        requests.post(url=f'{tg_service_url}/update', json=update)
    except Exception as e:
        LOG.error(str(e))
    finally:
        return Response(status=200)


if __name__ == '__main__':
    # wait 5s for ngrok to start up
    if not app_base_url:
        counter = 0
        while counter < 10:
            try:
                resp = requests.get(url="http://ngrok:4040/api/tunnels/command_line")
                app_base_url = resp.json()["public_url"]
                LOG.debug("App url set to %s", app_base_url)
                break
            except Exception as e:
                LOG.warn(str(e))
                time.sleep(5)
                counter += 1
    if app_base_url:
        webhook()
        app.run(host='0.0.0.0', port=8080)
    else:
        LOG.error("no APP_BASE_URL set and failed to fetch one from ngrok")
        exit(1)

    
