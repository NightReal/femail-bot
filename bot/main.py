from telethon import events, TelegramClient, Button
import os
from backend import db
import logging
import re
import email_handler
import hashlib


logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

bot = TelegramClient('bot', int(os.environ["API_ID"]), os.environ["API_HASH"]).start(bot_token=os.environ["BOT_TOKEN"])

BOTNAME = 'femail_bot'


class CMD:
    TOGGLE = 0
    MANAGE = 1
    MANAGE_BACK = 2
    MANAGE_TOGGLE = 3
    MANAGE_BWLIST = 4
    MANAGE_SHOW = 5


def gethash(email):
    return hashlib.md5(email.encode()).hexdigest()


@bot.on(events.NewMessage(pattern=fr'(?i)^/add({BOTNAME}|)(\s|$)', incoming=True))
async def add_email(event):
    text = event.raw_text
    match = re.search(fr'(?i)^/add({BOTNAME}|)(|\s+(.*?)(|\n(.*)))$', text, re.DOTALL)
    email = match.group(3)
    password = match.group(5)
    if not email_handler.validate(email):
        msg = 'Email address is incorrect'
    elif not password:
        msg = 'Password is empty'
    else:
        msg = f'Email: `{email}`\nPassword: `{password}`'
        emails = db.get(event.chat_id, 'emails')
        if emails is None:
            emails = dict()
        emails[gethash(email)] = {'address': email, 'password': password, 'active': True,
                                  'blacklist': [], 'whitelist': [], 'useblack': True}
        db.update(event.chat_id, emails=emails)
    await event.respond(msg)


def get_emails_buttons(emails, show_active_status=False, cmd=None):
    buttons = []
    for i, hsh in enumerate(emails):
        if i % 2 == 0:
            buttons.append([])
        email = emails[hsh]['address']
        if show_active_status:
            status = '✅' if emails[hsh]['active'] else '❌'
            text = f'{status}  {email}'
        else:
            text = email
        data = {'cmd': cmd, 'hash': hsh}
        buttons[-1].append(Button.inline(text, data=encode_obj(data)))
    return buttons


@bot.on(events.NewMessage(pattern=fr'(?i)^/toggle({BOTNAME}|)(\s|$)', incoming=True))
async def toggle(event):
    emails = db.get(event.chat_id, 'emails')
    if emails is None:
        await event.respond('You haven\'t added any email addresses')
        return
    msg = 'Start and stop receiving emails'
    buttons = get_emails_buttons(emails, show_active_status=True, cmd=CMD.TOGGLE)
    await event.respond(msg, buttons=buttons)


@bot.on(events.NewMessage(pattern=fr'(?i)^/manage({BOTNAME}|)(\s|$)', incoming=True))
async def manage(event, new=True):
    emails = db.get(event.chat_id, 'emails')
    if emails is None:
        await event.respond('You haven\'t added any email addresses')
        return
    msg = 'Choose email address'
    buttons = get_emails_buttons(emails, show_active_status=False, cmd=CMD.MANAGE)
    if new:
        await event.respond(msg, buttons=buttons)
    else:
        await bot.edit_message(event.chat_id, event.message_id, msg, buttons=buttons)


@bot.on(events.NewMessage(pattern=fr'(?i)^/edit_(blacklist|whitelist)({BOTNAME}|)(\s|$)', incoming=True))
async def edit_bwlist(event):
    text = event.raw_text
    match = re.search(fr'(?i)^/edit_(blacklist|whitelist)({BOTNAME}|)(|\s+(.*?)\n(.*))$', text, re.DOTALL)
    bwlist = match.group(1)
    email = match.group(4)
    raw_masks = match.group(5).split('\n')
    masks = []
    for mask in raw_masks:
        mask = mask.strip()
        if mask:
            masks.append(mask)
    emails = db.get(event.chat_id, 'emails')
    hsh = gethash(email)
    emails[hsh][bwlist] = masks
    db.update(event.chat_id, emails=emails)


def encode_obj(obj):
    m = []
    for k in obj:
        v = obj[k]
        if isinstance(v, bool):
            v = int(v)
        m.append(f'{k}:{v}')
    m = ','.join(m)
    return m.encode()


def decode_obj(bytes):
    d = {}
    for s in bytes.decode().split(','):
        k, v = s.split(':')
        if v.isdigit():
            v = int(v)
        d[k] = v
    return d


async def show_manage_email(event, hsh, email):
    receive_text = 'Receive emails ✅' if email['active'] else 'Don\'t receive emails ❌'
    receive_data = {'cmd': CMD.MANAGE_TOGGLE, 'hash': hsh}
    bwlist_text = 'Use blacklist' if email['useblack'] else 'Use whitelist'
    bwlist_data = {'cmd': CMD.MANAGE_BWLIST, 'hash': hsh}
    
    black_masks_count = len(email['blacklist'])
    bshow_text = f'Show blacklist ({black_masks_count} mask{"s" if black_masks_count != 1 else ""})'
    bshow_data = {'cmd': CMD.MANAGE_SHOW, 'hash': hsh, 'black': 1}
    
    white_masks_count = len(email['whitelist'])
    wshow_text = f'Show whitelist ({white_masks_count} mask{"s" if white_masks_count != 1 else ""})'
    wshow_data = {'cmd': CMD.MANAGE_SHOW, 'hash': hsh, 'black': 0}
    
    back_text = '⬅️ Back'
    back_data = {'cmd': CMD.MANAGE_BACK}

    msg = f'Manage email address: `{email["address"]}`'
    buttons = [[Button.inline(receive_text, data=encode_obj(receive_data))],
               [Button.inline(bwlist_text, data=encode_obj(bwlist_data))],
               [Button.inline(bshow_text, data=encode_obj(bshow_data)), Button.inline(wshow_text, data=encode_obj(wshow_data))],
               [Button.inline(back_text, data=encode_obj(back_data))]]

    await bot.edit_message(event.chat_id, event.message_id, msg, buttons=buttons)


def toggle_email(chat_id, hsh):
    emails = db.get(chat_id, 'emails')
    emails[hsh]['active'] = not emails[hsh]['active']
    db.update(chat_id, emails=emails)
    return emails


async def callback_toggle(event, edata):
    hsh = edata['hash']
    emails = toggle_email(event.chat_id, hsh)
    buttons = get_emails_buttons(emails, show_active_status=True, cmd=CMD.TOGGLE)
    await bot.edit_message(event.chat_id, event.message_id, buttons=buttons)


async def callback_manage_toggle_email(event, edata):
    hsh = edata['hash']
    email = toggle_email(event.chat_id, hsh)[hsh]
    await show_manage_email(event, hsh, email)


async def callback_manage_toggle_bwlist(event, edata):
    hsh = edata['hash']
    emails = db.get(event.chat_id, 'emails')
    emails[hsh]['useblack'] = not emails[hsh]['useblack']
    db.update(event.chat_id, emails=emails)
    await show_manage_email(event, hsh, emails[hsh])


async def callback_manage(event, edata):
    hsh = edata['hash']
    email = db.get(event.chat_id, 'emails')[hsh]
    await show_manage_email(event, hsh, email)


async def callback_manage_show(event, edata):
    hsh = edata['hash']
    email = db.get(event.chat_id, 'emails')[hsh]
    message_0 = ['Whitelist — only email addresses whose messages will be forwarded.',
                 'Blacklist — email addresses whose messages won\'t be forwarded.'][edata['black']] + '\n\n'
    masks = email['blacklist'] if email['useblack'] else email['whitelist']
    if len(masks) == 0:
        msg = message_0 + '**The list is empty.**'
    else:
        msg = message_0 + '\n'.join((f'`{mask}`' for mask in masks))
    await event.respond(msg)


@bot.on(events.CallbackQuery())
async def callback(event):
    edata = decode_obj(event.data)
    if edata['cmd'] == CMD.TOGGLE:
        await callback_toggle(event, edata)
    elif edata['cmd'] == CMD.MANAGE:
        await callback_manage(event, edata)
    elif edata['cmd'] == CMD.MANAGE_BACK:
        await manage(event, new=False)
    elif edata['cmd'] == CMD.MANAGE_TOGGLE:
        await callback_manage_toggle_email(event, edata)
    elif edata['cmd'] == CMD.MANAGE_BWLIST:
        await callback_manage_toggle_bwlist(event, edata)
    elif edata['cmd'] == CMD.MANAGE_SHOW:
        await callback_manage_show(event, edata)
    else:
        print('Unexpected callback:', edata)


bot.run_until_disconnected()
