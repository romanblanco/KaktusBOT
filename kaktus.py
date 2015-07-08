import sys
import time
import http.client
import urllib.parse
import urllib.request
import socket
import re
import logging
import json
import threading
import signal

DEBUG = False
LOADING_TIME = 60*30
RECEIVING_TIME = 2
TOKEN = "*********************************************"


class Application:

    def __init__(self):
        self.telegram = Telegram(self)
        self.subscribers = Subscribers()
        self.article = Article()
        # start receiving thread
        self.threading = threading.Thread(target=self.receivingThread)
        logging.debug('setting thread as daemon')
        self.threading.daemon = True
        logging.debug('starting thread as daemon')
        self.threading.start()
        # start main
        logging.debug('continue with main')
        self.main()

    def main(self):
        while True:
            logging.debug('next loading iteration')
            source = Connection.loadSource()
            regex = "<h3.+?>(?:<a.+?>(.+?)<\/a>|(.+?))<\/h3>.+?" \
                    "<p>(?:<p>)?\s(.+?)<\/p>"
            result = re.search(regex, source)
            loadedArticle = (result.group(1) or result.group(2)) + ' ' \
                + result.group(3)
            logging.debug('loaded article: "' + loadedArticle + '"')
            if self.article.new(loadedArticle):
                self.article.update(loadedArticle)
                for subscriber in self.subscribers.subscribersList():
                    self.telegram.sendMessage(int(subscriber), loadedArticle)
            time.sleep(LOADING_TIME)

    def receivingThread(self):
        """Thread that handles receiving messages"""
        logging.debug('starting receiving thread')
        while True:
            logging.debug('next iteration of receiving thread')
            time.sleep(RECEIVING_TIME)
            if self.telegram.checkOnline():
                self.telegram.update()

    def interpret(self, response):
        """From response recognize which action should be done"""
        logging.debug('interpreting response: ' + str(response))
        if 'text' in response['message'].keys():
            if response['message']['text'] == "/subscribe":
                self.addSubscriber(response['message']['from']['id'])
            elif response['message']['text'] == "/unsubscribe":
                self.removeSubscriber(response['message']['from']['id'])
            elif response['message']['text'] == "/last":
                self.showLast(response['message']['from']['id'])

    def addSubscriber(self, userId):
        """Add new subscriber to list"""
        if self.subscribers.add(userId):
            self.telegram.sendMessage(
                userId,
                "You're now subscribing news from Kaktus operator")
        else:
            self.telegram.sendMessage(
                userId,
                "You are already subscribing news from Kaktus operator")

    def removeSubscriber(self, userId):
        """Remove subscriber from list"""
        if self.subscribers.remove(userId):
            self.telegram.sendMessage(
                userId,
                "You were removed from subscribing news from Kaktus operator")
        else:
            self.telegram.sendMessage(
                userId,
                "You weren't subscribing news from Kaktus operator")

    def showLast(self, userId):
        """Show newest article"""
        if self.article.lastArticle() != '':
            self.telegram.sendMessage(userId, self.article.lastArticle())
        else:
            self.telegram.sendMessage(userId, "No articles loaded yet.")

    def help(self, userId):
        """Send help message with available commands to user"""
        # TODO: write help message
        helpMessage = ""
        self.telegram.sendMessage(userId, helpMessage)


class Connection:
    """Loading website source"""

    def loadSource():
        """Load source of page with news"""
        connection = http.client.HTTPSConnection("www.mujkaktus.cz")
        try:
            connection.request("GET", "/novinky")
        except socket.gaierror:
            logging.error("nepodarilo se nacist data z webove stranky")
        response = connection.getresponse()
        content = response.read().decode('utf-8')
        return content


class Telegram:

    def __init__(self, application):
        self.app = application
        self.lastUpdatedId = 0
        self.apiUrl = 'https://api.telegram.org/bot' + TOKEN + '/'

    def checkOnline(self):
        """From response decides if Bot connection with server is working"""
        response = self.sendRequest("getMe")
        return json.JSONDecoder().decode(response)['ok']

    def update(self):
        """Load last messages sent to Bot"""
        updates = self.sendRequest("getUpdates", offset=self.lastUpdatedId)
        messages = json.JSONDecoder().decode(updates)
        logging.debug('loaded ' + str(len(messages)) + ' messages in update')
        updatedId = messages['result'][len(messages['result'])-1]['update_id']
        if messages and updatedId != self.lastUpdatedId:
            for message in messages['result']:
                if message['update_id'] > self.lastUpdatedId:
                    self.app.interpret(message)
            # store last update id
            self.lastUpdatedId = updatedId
            logging.debug('new last update id: ' + str(self.lastUpdatedId))

    def sendMessage(self, chatId, message):
        """Send message from bot to specific chat"""
        self.sendRequest("sendMessage", chat_id=chatId, text=message)

    def sendRequest(self, method, **kwargs):
        """Sending requests to Telegram API and returns response"""
        data = urllib.parse.urlencode(kwargs)
        logging.debug('sending request: ' + self.apiUrl + method + '?' + data)
        try:
            request = urllib.request.urlopen(self.apiUrl + method + '?' + data)
        except urllib.error.URLError:
            logging.error('It looks like there are issues with connection')
            sys.exit(2)
        return request.read().decode('utf-8')


class Subscribers:
    """Keep users IDs"""

    def __init__(self):
        self.subscribers = []

    def add(self, userId):
        """Add user's ID to list of subscribers"""
        if str(userId) not in self.subscribers:
            self.subscribers.append(str(userId))
            logging.debug('new subscriber: ' + str(self.subscribers))
            return True
        else:
            return False

    def remove(self, userId):
        """Remove user's ID from list of subscribers"""
        if str(userId) in self.subscribers:
            self.subscribers.remove(str(userId))
            logging.debug('one subscriber removed: ' + str(self.subscribers))
            return True
        else:
            return False

    def subscribersList(self):
        """Return list with all subscribers IDs"""
        return self.subscribers


class Article:
    """Load and return articles from website"""

    def __init__(self):
        self.last = ''

    def lastArticle(self):
        """Return last article"""
        return self.last

    def update(self, article):
        """Update article when new one appears"""
        self.last = article

    def new(self, article):
        """Compare if loaded article is new or not"""
        return (article != self.last)


class LogFilter:
    """Filtering log messages with higher level"""

    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


def signal_handler(signal, frame):
    """Pri zachyceni signalu ukonci skript"""
    print("\nBye bye...")
    sys.exit(0)


def setLogging():
    """Logging configuration. For 'debug' mode set DEBUG constant to True"""
    # logging configuration
    logger = logging.getLogger()
    logformat = '%(levelname)s:%(asctime)s (l.%(lineno)d) -- %(message)s\n'
    logger.setLevel(logging.DEBUG)
    # info log
    handler = logging.FileHandler('log.txt', 'w')
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(logformat)
    handler.setFormatter(formatter)
    handler.addFilter(LogFilter(logging.INFO))
    logger.addHandler(handler)
    # error log
    handler = logging.FileHandler('error_log.txt', 'w')
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(logformat)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # debug to stdout
    if DEBUG:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(logformat)
        handler.setFormatter(formatter)
        handler.addFilter(LogFilter(logging.DEBUG))
        logger.addHandler(handler)

if __name__ == '__main__':
    sys.stdout.write("\x1b]2;Kaktus BOT\x07")
    signal.signal(signal.SIGINT, signal_handler)
    setLogging()
    app = Application()

# vi: sts=4 et sw=4
