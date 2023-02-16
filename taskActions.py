from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from redmine import getRedmine, getUser

# Возвращает текст с описанием задачи
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

# Отправка информации о задачи
async def sendIssue(issue, message, bot):
    status = issue.status.name
    text = getIssueText(issue)
    common = [
        InlineKeyboardButton('Подробнее', None, callback_data=f'details:{issue.id}'),
        InlineKeyboardButton('К задаче', url=f'https://redmine.tech.rightstep.ru/issues/{issue.id}')
    ]
    actions = []
    if status in ["К разработке", "Новый", "Отложенный"]:
        actions.append(InlineKeyboardButton('В работу', None, callback_data=f'toWork:{issue.id}'))
    if status == "В работе":
        actions.append(InlineKeyboardButton('В тест', None, callback_data=f'toTest:{issue.id}'))
        actions.append(InlineKeyboardButton('К сборке (Front)', None, callback_data=f'toAssembly:{issue.id}'))
        
    markup = InlineKeyboardMarkup([common, actions])

    await bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="html")

# Нет задач по фильтру
async def sendHasNoIssues(chatID, bot):
    text = "Я не нашел ни одной задачи по указанному фильтру 🤷‍♂️"
    return await bot.send_message(chatID, text)

# Удаление сообщения
async def deleteMessage(call, bot):
    splited = call.data.split(':')
    chatID = int(splited[1])
    messageID = call.message.id
    await bot.answer_callback_query(call.id, "Скрыл это сообщение для тебя ❤️")
    await bot.delete_message(chatID, messageID)

# Просмотр детального описания задачи
async def showDetails(call, bot):
    chatID = call.message.chat.id
    redmine = getRedmine(chatID)
    issueId = int(call.data.split(':')[1])
    issue = redmine.issue.get(issueId)
    text = issue.description
    markup = InlineKeyboardMarkup([[InlineKeyboardButton('Скрыть', None, callback_data=f'deleteMessage:{chatID}')]])
    await bot.reply_to(call.message, text, reply_markup=markup, parse_mode='html')

# Просмотр моих задач в версии
async def showTasksByVersion(call, bot):
    chatID = call.message.chat.id
    redmine = getRedmine(chatID)
    user = getUser(chatID)

    versionID = call.data.split(':')[1]
    issues = redmine.issue.filter(assigned_to_id=user.id)
    issuesInVersion = []
    
    if versionID == 'null':
        issuesInVersion = list(filter(lambda issue: not hasattr(issue, 'fixed_version'), list(issues)))
    else:
        issuesInVersion = list(filter(lambda issue: issue.fixed_version.id == int(versionID) if hasattr(issue, 'fixed_version') else False, list(issues)))
    
    if len(issuesInVersion) == 0:
        return await sendHasNoIssues(chatID, bot)

    for issue in issuesInVersion:
        await sendIssue(issue, call.message, bot)

# Перевод задачи в работу
async def toWork(call, bot):
    redmine = getRedmine(call.message.chat.id)
    issueId = int(call.data.split(':')[1])
    # 2 - id статус "В работе"
    redmine.issue.update(issueId, status_id=2)
    issue = redmine.issue.get(issueId)
    text = f'Готово! Задача в работе, скорее за дело! 🐱'
    await bot.reply_to(call.message, text)
    await sendIssue(issue, call.message, bot)

# Перевод задачи в тестирование
async def toTest(call, bot):
    redmine = getRedmine(call.message.chat.id)
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

async def toAssembly(call, bot):
    redmine = getRedmine(call.message.chat.id)
    issueId = int(call.data.split(':')[1])
    issue = redmine.issue.get(issueId)
    # 60 - id Зимина Алексея
    user = redmine.user.get(60)

    custom_fields = list(issue.custom_fields.values())
    for field in custom_fields:
        if field["name"] == 'К сборке':
            field["value"] = 1

    redmine.issue.update(issueId,
        # 9 - id статус "Тест"
        status_id=9,
        assigned_to_id=user.id,
        done_ratio=100,
        notes="Выполнено. Прошу включить в сборку",
        custom_fields=custom_fields
    )

    text = f'Спасибо! Задача отправлена на сборку 🫂'
    await bot.reply_to(call.message, text)