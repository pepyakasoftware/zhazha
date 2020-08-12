import logging
import re
import sys
from collections import defaultdict
import redis
import json
from random import choice

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOG = logging.getLogger('markov:markov')
redis_url="redis"

re_alphabet = re.compile('[0-9а-яА-ЯёЁіІїЇєЄґҐ-]+|[.,:;?!]')
re_brackets = re.compile('<.*>')
re_emoji = re.compile(':[^\s]+:')

_client = redis.Redis(host=redis_url, db=0)

def generate_sentences(dictionary_id: int, t1: str = None, amount: int = None) -> str:
    t1 = t1 or '$'
    amount = amount or 1
    sentences = []
    for i in range(amount):
        if i == 0:
            sentence = _generate_sentence(dictionary_id, t1)
        else:
            sentence = _generate_sentence(dictionary_id)
        sentences.append(sentence)
    return ' '.join(sentences)


def _generate_sentence(dictionary_id: int, t1: str = '$') -> str:
    phrase = ''
    t0 = '$'
    if t1 != '$':
        phrase += t1
    while True:
        key=f'{str(dictionary_id)}:{t0}:{t1}'
        seq = [e.decode("utf-8") for e in _client.smembers(key)]
        LOG.debug("Key: %s, seq: %s", key, seq)
        if not seq:
            phrase += "!"
            break
        t0, t1 = t1, choice(seq)
        if t1 == '$':
            break
        if t1 in '.!?,;:' or t0 == '$':
            phrase += t1
        else:
            phrase += ' ' + t1
    LOG.debug(str(phrase))
    return phrase.capitalize()


def train_model(dictionary_id: int, corpus: str):
    LOG.debug('Train corpus: %s', corpus)
    entities = []
    lines = _gen_lines(corpus)
    tokens = _gen_tokens(lines)
    trigrams = _gen_trigrams(tokens)
    bi, tri = defaultdict(lambda: 0.0), defaultdict(lambda: 0.0)
    for t0, t1, t2 in trigrams:
        bi[t0, t1] += 1
        tri[t0, t1, t2] += 1
    entities=[]
    for (t0, t1, t2), freq in tri.items():
        key = f'{str(dictionary_id)}:{t0}:{t1}'
        _client.sadd(key, t2)
        entities.append(f'{key}:{t2}')
    LOG.debug('Training result: %s', entities)
 

def _gen_lines(text: str):
    text = re_brackets.sub(' ', text)
    text = re_emoji.sub(' ', text)
    lines = text.splitlines()
    for line in lines:
        if line[-1:].isalpha():
            line += '.'
        yield line


def _gen_tokens(lines):
    for line in lines:
        tokens = re_alphabet.findall(line)
        if len(tokens) > 3:
            for token in tokens:
                yield token


def _gen_trigrams(tokens):
    t0, t1 = '$', '$'
    for t2 in tokens:
        if t0 == t1 == "$" and not t2.isalpha():
            t0, t1 = t1, t2
            continue
        yield t0, t1, t2
        if t2 in '.!?':
            yield t1, t2, '$'
            yield t2, '$', '$'
            t0, t1 = '$', '$'
        else:
            t0, t1 = t1, t2
