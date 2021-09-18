from telethon import events, TelegramClient, Button
import os
from backend import db
import logging
import re
import email_handler


logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

bot = TelegramClient('bot', int(os.environ["API_ID"]), os.environ["API_HASH"]).start(bot_token=os.environ["BOT_TOKEN"])

BOTNAME = 'femail_bot'


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
        emails[email] = {'address': email, 'password': password, 'active': True}
        db.update(event.chat_id, emails=emails)
    await event.respond(msg)


@bot.on(events.NewMessage(pattern=fr'(?i)^/emails({BOTNAME}|)(\s|$)', incoming=True))
async def add_email(event):
    emails = db.get(event.chat_id, 'emails')
    if emails is None:
        await event.respond('You haven\'t added any email addresses')
        return
    msg = ['Your email addresses:']
    for email in emails:
        msg.append(f'`{email}`')
    msg = '\n'.join(msg)
    await event.respond(msg)


def get_manage_buttons(emails):
    buttons = []
    for i, email in enumerate(emails):
        if i % 2 == 0:
            buttons.append([])
        status = '✅' if emails[email]['active'] else '❌'
        buttons[-1].append(Button.inline(f'{email} {status}', data=repr(emails[email])))
    return buttons


@bot.on(events.NewMessage(pattern=fr'(?i)^/manage({BOTNAME}|)(\s|$)', incoming=True))
async def manage(event):
    emails = db.get(event.chat_id, 'emails')
    if emails is None:
        await event.respond('You haven\'t added any email addresses')
        return
    msg = 'Active and inactive emails'
    buttons = get_manage_buttons(emails)
    await event.respond(msg, buttons=buttons)


@bot.on(events.CallbackQuery())
async def callback(event):
    email = eval(event.data)
    emails = db.get(event.chat_id, 'emails')
    emails[email['address']]['active'] = not email['active']
    db.update(event.chat_id, emails=emails)

    buttons = get_manage_buttons(emails)
    await bot.edit_message(event.chat_id, event.message_id, buttons=buttons)


bot.run_until_disconnected()
