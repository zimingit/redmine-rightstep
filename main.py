# msg = ("Ready, take a look:\n<b>"
#                f"Name: {data['name']}\n"
#                f"Surname: {data['surname']}\n"
#                f"Age: {message.text}</b>")
#         bot.send_message(message.chat.id, msg, parse_mode="html")

import asyncio
import telegram
import sotrings
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

def getIssueText(issue):
    trackerIcons = {
        "BUG": "🐞",
        "FEAT": "💡",
        "Заявка": "❔"
    }
    tracker = trackerIcons.get(issue.tracker.name, issue.tracker.name)
    number = issue.id
    status = issue.status.name
    priority = issue.priority.name
    version = issue.fixed_version.name if hasattr(issue, 'fixed_version') else 'Без версии'
    return (f"<b>{tracker} {number}</b>: {status} (<b>{priority}</b>) | <b>{version}</b>\n\n"
            f"{issue.subject}\n")

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
        try:
            setRedmine(data['username'], message.text)
            text = (f"Блестяще, теперь ты <b>авторизован</b>! 😍\n"
                    f"Посмотрим твои задачи?")
            markup = types.InlineKeyboardMarkup([[
                types.InlineKeyboardButton(
                    'Мои задачи', None, callback_data='/mytasks')
            ]])
            await bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="html")
            await bot.delete_state(message.from_user.id, message.chat.id)
        except:
            text = (f"Упс, кажется введенные <b>данные не подошли</b>...🥲\n"
                    f"Давай попробуем еще раз. <b>Вводи логин</b> 🤞")
            await bot.set_state(message.from_user.id, MyStates.username, message.chat.id)
            await bot.send_message(message.chat.id, text, parse_mode="html")



# Список задач
@bot.message_handler(commands=['mytasks'])
async def sendTasks(message):
    global user
    issues = redmine.issue.filter(assigned_to_id=user.id)
    await bot.send_message(message.chat.id, "Список твоих задач:")
    # issue.fixed_version
    async def sendIssue(issue):
        status = issue.status.name
        text = getIssueText(issue)

        buttons = [types.InlineKeyboardButton('Подробнее', None, callback_data=f'details:{issue.id}')]
        if status in ["К разработке", "Новый", "Отложенный"]:
            buttons.append(types.InlineKeyboardButton('В работу', None, callback_data=f'toWork:{issue.id}'))
        if status == "В работе":
            buttons.append(types.InlineKeyboardButton('В тест', None, callback_data=f'toTest:{issue.id}'))
        buttons.append(types.InlineKeyboardButton('К задаче', url=f'https://redmine.tech.rightstep.ru/issues/{issue.id}'))

        markup = types.InlineKeyboardMarkup([buttons])

        await bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="html")

    issuesByVersion = sorted(issues, key=sotrings.sortByVersion)
    for issue in issuesByVersion:
        await sendIssue(issue)

# Обработка нажатия кнопок под задачей
@bot.callback_query_handler(func=None)
async def back_callback(call: types.CallbackQuery):
    if call.data == '/mytasks':
        return await sendTasks(call.message)
    
    async def showDetails(call):
        global redmine
        issueId = int(call.data.split(':')[1])
        issue = redmine.issue.get(issueId)
        text = issue.description
        await bot.reply_to(call.message, text, parse_mode='html')

    async def toWork(call):
        global redmine
        issueId = int(call.data.split(':')[1])
        # 2 - id статус "В работе"
        redmine.issue.update(issueId, status_id=2)
        text = f'Готово! Задача в работе, скорее за дело! 🐱'
        await bot.reply_to(call.message, text)

    async def toTest(call):
        global redmine
        issueId = int(call.data.split(':')[1])
        issue = redmine.issue.get(issueId)
        
        custom_fields = list(issue.custom_fields.values())
        for field in custom_fields:
            if field["name"] == 'К сборке':
                field["value"] = 1

        redmine.issue.update(issueId,
            # 9 - id статус "Тест"
            status_id=9,
            assigned_to_id=issue.author.id,
            done_ratio=100,
            notes="Выполнено",
            custom_fields=custom_fields
        )

        text = f'Супер! Задача отправлена на тестирование 🥰'
        await bot.reply_to(call.message, text)

    if call.data.startswith('details'):
        return await showDetails(call)
    
    if call.data.startswith('toWork'):
        return await toWork(call)
    if call.data.startswith('toTest'):
        return await toTest(call)
        

bot.add_custom_filter(asyncio_filters.StateFilter(bot))
asyncio.run(bot.polling())
