# msg = ("Ready, take a look:\n<b>"
#                f"Name: {data['name']}\n"
#                f"Surname: {data['surname']}\n"
#                f"Age: {message.text}</b>")
#         bot.send_message(message.chat.id, msg, parse_mode="html")

import asyncio
import telegram
from telebot.async_telebot import AsyncTeleBot
from redminelib import Redmine
from telebot import types, asyncio_filters

from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.asyncio_storage import StateMemoryStorage

bot = AsyncTeleBot(telegram.token, state_storage=StateMemoryStorage())


class MyStates(StatesGroup):
    username = State()
    password = State()


redmine = None
project = None
user = None


def setRedmine(username, password):
    global redmine
    global project
    global user
    redmine = Redmine('https://redmine.tech.rightstep.ru/',
                      username=username, password=password)
    user = redmine.auth()
    project = redmine.project.get('scmo-3-x')

# Приветственное сообщение


@bot.message_handler(commands=['start', 'login'])
async def send_welcome(message):
    await bot.set_state(message.from_user.id, MyStates.username, message.chat.id)
    await bot.send_message(message.chat.id, """\
Привет!
Я помогу тебе разобраться с твоими задачами в <b>Redmine</b>.
Для начала давай войдём в твой аккаунт 😎\n
<b>Отправь мне свой логин</b>, чтобы мы начали авторизацию ✌️
\
""", parse_mode="html")

# Обработка логина


@bot.message_handler(state=MyStates.username)
async def username_set(message):
    """
    Сработает, когда состояние будет установлено в username
    """
    text = ("Отлично, теперь <b>вводи пароль</b> и я авторизую тебя 👌\nНе переживай, я не подглядываю 😉")
    await bot.send_message(message.chat.id, text, parse_mode="html")
    await bot.set_state(message.from_user.id, MyStates.password, message.chat.id)
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['username'] = message.text

# Обработка пароля


@bot.message_handler(state=MyStates.password)
async def password_set(message):
    global redmine
    """
    Сработает, когда состояние будет установлено в password
    """
    async with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        setRedmine(data['username'], message.text)
        text = ("Блестяще, теперь ты <b>авторизован</b>! 😍\nПосмотрим твои задачи?")
        markup = types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton(
                'Мои задачи', None, callback_data='/mytasks')
        ]])
        await bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="html")
        await bot.delete_state(message.from_user.id, message.chat.id)


# Список задач
@bot.message_handler(commands=['mytasks'])
async def send_tasks(message):
    global user
    issues = redmine.issue.filter(assigned_to_id=user.id)
    await bot.send_message(message.chat.id, "Список твоих задач:")

    async def sendIssue(issue):
        text = f'*{issue.id}*: {issue.subject}'
        url = f'https://redmine.tech.rightstep.ru/issues/{issue.id}'
        markup = types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton(
                'Подробнее', None, callback_data=issue.id),
            types.InlineKeyboardButton('К задаче', url=url)
        ]])
        await bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

    for issue in issues:
        await sendIssue(issue)

# Обработка нажатия кнопок под задачей


@bot.callback_query_handler(func=None)
async def back_callback(call: types.CallbackQuery):
    if call.data == '/mytasks':
        return await send_tasks(call.message)

    global redmine
    issue = redmine.issue.get(int(call.data))
    text = issue.description
    # text = '\n'.join([f'{issue.id}: {issue.subject}', issue.description])
    # text = '\n'.join([issue.id, issue.subject, issue.description])
    await bot.reply_to(call.message, text, parse_mode='Markdown')

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
asyncio.run(bot.polling())
