from redminelib import Redmine

sessionUsersStorage = {}
redmineUrl = 'https://redmine.tech.rightstep.ru/'

def getStorage(chatID):
    return sessionUsersStorage[chatID]

def getRedmine(chatID):
    return getStorage(chatID)["redmine"]

def getProject(chatID):
    return getStorage(chatID)["project"]

def getUser(chatID):
    return getStorage(chatID)["user"]

def setRedmine(chatID, username, password):
    redmine = Redmine(redmineUrl, username=username, password=password)
    user = redmine.auth()
    project = redmine.project.get('scmo-3-x')
    sessionUsersStorage[chatID] = {
        'username': username,
        'password': password,
        'redmine': redmine,
        'project': project,
        'user': user
    }