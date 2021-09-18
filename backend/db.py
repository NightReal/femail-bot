from copy import deepcopy

data_base = dict()


def update(chat_id, **kwargs):
    global data_base
    if chat_id not in data_base:
        data_base[chat_id] = dict()
    data_base[chat_id].update(kwargs)


def getval(d, *keys):
    for k in keys:
        if k not in d:
            return None
        d = d[k]
    return d


def get_many(chat_id, *args):
    global data_base
    return (deepcopy(getval(data_base, chat_id, key)) for key in args)


def get(chat_id, key):
    global data_base
    return deepcopy(getval(data_base, chat_id, key))
