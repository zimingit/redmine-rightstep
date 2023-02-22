import asyncio
import taskActions
from redminelib import Redmine

sessionUsersStorage = {}
redmineUrl = 'https://redmine.tech.rightstep.ru/'

# Проверка новых задач
async def useNotificator(chatID, bot):
    issues = getIssues(chatID)
    newIssues = list(filter(lambda issue: issue.isNew == True, issues))
    if newIssues:
        text = f"Тадам! Встречай {'новую задачу' if len(newIssues) == 1 else 'новые задачи'}! 🥳"
        await bot.send_message(chatID, text)
        for issue in newIssues:
            await taskActions.sendIssue(issue, chatID, bot)
    else:
        print('Нет новых задач')
    
    tenMinutes = 600
    await asyncio.sleep(tenMinutes)
    await useNotificator(chatID, bot)

def getStorage(chatID):
    isLoggedIn = sessionUsersStorage[chatID]["redmine"]
    try:
        isLoggedIn.auth()
        return sessionUsersStorage[chatID]
    except:
        username = sessionUsersStorage[chatID]["username"]
        password = sessionUsersStorage[chatID]["password"]
        setRedmine(chatID, username, password)
        return sessionUsersStorage[chatID]

def getRedmine(chatID):
    return getStorage(chatID)["redmine"]

def getProject(chatID):
    return getStorage(chatID)["project"]

def getUser(chatID):
    return getStorage(chatID)["user"]

def getIssues(chatID):
    redmine = getRedmine(chatID)
    user = getUser(chatID)
    oldIssuesIds = []
    for issue in getStorage(chatID)["issues"]:
        oldIssuesIds.append(issue.id)

    issues = list(redmine.issue.filter(assigned_to_id=user.id))
    for issue in issues:
        isNew = not issue.id in oldIssuesIds
        issue.isNew = isNew
    sessionUsersStorage[chatID]["issues"] = issues
    return issues

def setRedmine(chatID, username, password):
    redmine = Redmine(redmineUrl, username=username, password=password)
    user = redmine.auth()
    project = redmine.project.get('scmo-3-x')
    issues = list(redmine.issue.filter(assigned_to_id=user.id))
    sessionUsersStorage[chatID] = {
        'username': username,
        'password': password,
        'redmine': redmine,
        'project': project,
        'issues': issues,
        'user': user
    }