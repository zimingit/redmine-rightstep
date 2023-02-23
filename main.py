import os
import asyncio
import sotrings
# import telegram
import taskActions
from redmine import setRedmine, getProject, getIssues, useNotificator 
from telebot.async_telebot import AsyncTeleBot
from telebot import types, asyncio_filters
from telebot.asyncio_handler_backends import State, StatesGroup
from telebot.asyncio_storage import StateMemoryStorage

bot = AsyncTeleBot(os.environ.get('TELEGRAM'), state_storage=StateMemoryStorage())
class MyStates(StatesGroup):
    username = State()
    password = State()

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
    """
    Сработает, когда состояние будет установлено в password
    """
    chatID = message.chat.id
    async with bot.retrieve_data(message.from_user.id, chatID) as data:
        try:
            setRedmine(chatID, data['username'], message.text)
            text = (f"Блестяще, теперь ты <b>авторизован</b>! 😍\n"
                    f"Посмотрим твои задачи?")
            markup = types.InlineKeyboardMarkup([[
                types.InlineKeyboardButton('Задачи на мне', None, callback_data='/mytasks'),
                types.InlineKeyboardButton('По версии', None, callback_data='/tasks')
            ]])
            await bot.send_message(chatID, text, reply_markup=markup, parse_mode="html")
            await bot.delete_state(message.from_user.id, chatID)
            await useNotificator(chatID, bot)
        except:
            text = (f"Упс, кажется введенные <b>данные не подошли</b>...🥲\n"
                    f"Давай попробуем еще раз. <b>Вводи логин</b> 🤞")
            await bot.set_state(message.from_user.id, MyStates.username, chatID)
            await bot.send_message(chatID, text, parse_mode="html")


# Список всех задач
@bot.message_handler(commands=['mytasks'])
async def sendMyTasks(message):
    chatID = message.chat.id
    issues = getIssues(chatID)
    issuesByVersion = sorted(issues, key=sotrings.sortByVersion)
    if len(issuesByVersion) == 0:
        return await taskActions.sendHasNoIssues(chatID, bot)
    
    await bot.send_message(chatID, "Список твоих задач:")
    for issue in issuesByVersion:
        await taskActions.sendIssue(issue, message.chat.id, bot) 

# Список задач по версии
@bot.message_handler(commands=['tasks'])
async def sendTasks(message):
    project = getProject(message.chat.id)
    versions = list(filter(lambda version: version.status == 'open', list(project.versions)))
    text = "Задачи какой из версий ты хочешь посмотреть? 🧐"
    buttons = [types.InlineKeyboardButton('Без версии', None, callback_data=f'showTasksByVersion:null')]

    for version in versions:
        buttons.append(types.InlineKeyboardButton(version.name, None, callback_data=f'showTasksByVersion:{version.id}'))
    markup = types.InlineKeyboardMarkup([buttons])
    await bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработка нажатия кнопок под задачей
@bot.callback_query_handler(func=None)
async def back_callback(call: types.CallbackQuery):
    if call.data == '/mytasks':
        return await sendMyTasks(call.message)
    if call.data == '/tasks':
        return await sendTasks(call.message)
    if call.data.startswith('deleteMessage'):
        return await taskActions.deleteMessage(call, bot)

    if call.data.startswith('details'):
        return await taskActions.showDetails(call, bot)
    if call.data.startswith('showTasksByVersion'):
        return await taskActions.showTasksByVersion(call, bot)
    if call.data.startswith('toWork'):
        return await taskActions.toWork(call, bot)
    if call.data.startswith('toAssembly'):
        return await taskActions.toAssembly(call, bot)
    if call.data.startswith('toTest'):
        return await taskActions.toTest(call, bot)


bot.add_custom_filter(asyncio_filters.StateFilter(bot))
    
asyncio.run(bot.polling())