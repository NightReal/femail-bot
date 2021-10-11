from copy import deepcopy
import os
import json

TMP_PATH = '../tmp'
DB_PATH = os.path.join(TMP_PATH, 'db.json')

data_base = dict()
if os.path.exists(DB_PATH):
    with open(DB_PATH) as f:
        data_base = json.load(f)


def dump_db():
    if not os.path.exists(TMP_PATH):
        os.mkdir(TMP_PATH)
    with open(DB_PATH, 'w') as f:
        json.dump(data_base, f, indent=4)


def update(chat_id, **kwargs):
    global data_base
    chat_id = str(chat_id)
    if chat_id not in data_base:
        data_base[chat_id] = dict()
    data_base[chat_id].update(kwargs)
    dump_db()


def getval(d, *keys):
    for k in keys:
        if k not in d:
            return None
        d = d[k]
    return d


def get_many(chat_id, *args):
    global data_base
    chat_id = str(chat_id)
    return (deepcopy(getval(data_base, chat_id, key)) for key in args)


def get(chat_id, key):
    global data_base
    chat_id = str(chat_id)
    return deepcopy(getval(data_base, chat_id, key))
