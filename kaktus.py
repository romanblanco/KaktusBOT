#!/usr/bin/env python3

import sys
import time
import http.client
import urllib.parse
import urllib.request
import socket
import re
import logging
import signal
from json import JSONDecoder
from threading import Thread

DEBUG = False
LOADING_TIME = 60*30


class Application:

    def __init__(self):
        self.bot = Telegram(" --- YOUR TELEGRAM BOT TOKEN --- ")
        self.subscribers = Subscribers()
        self.article = Article()
        # start receiving thread
        self.threading = Thread(target=self.receivingThread)
        self.threading.daemon = True
        self.threading.start()
        # start main
        self.main()

    def main(self):
        while True:
            logging.debug('next iteration of loading thread')
            source = Connection.loadSource()
            if source is not None:
                regex = "<h3.+?>(?:<a.+?>(.+?)<\/a>|(.+?))<\/h3>.+?" \
                        "<p>(?:<p>)?\s(.+?)<\/p>"
                result = re.search(regex, source)
                loadedArticle = (result.group(1) or result.group(2)) + ' ' \
                    + result.group(3)
                logging.debug('loaded article: "' + loadedArticle + '"')
                if self.article.new(loadedArticle):
                    self.article.updateArticle(loadedArticle)
                    for subscriber in self.subscribers.subscribersList():
                        self.bot.sendMessage(int(subscriber), loadedArticle)
            time.sleep(LOADING_TIME)

    def receivingThread(self):
        """Thread that handles receiving messages"""
        while True:
            logging.debug('next iteration of receiving thread')
            response = self.bot.update()
            if response is not None:
                self.interpret(response)

    def interpret(self, response):
        """From response recognize which action should be done"""
        logging.debug('interpreting response: ' + str(response))
        for message in response:
            if 'text' in message['message'].keys():
                if message['message']['text'] == "/subscribe":
                    self.addSubscriber(message['message']['from']['id'])
                elif message['message']['text'] == "/unsubscribe":
                    self.removeSubscriber(message['message']['from']['id'])
                elif message['message']['text'] == "/last":
                    self.showLast(message['message']['from']['id'])

    def addSubscriber(self, userId):
        """Add new subscriber to list"""
        if self.subscribers.add(userId):
            self.bot.sendMessage(
                userId,
                "You're now subscribing news from Kaktus operator")
        else:
            self.bot.sendMessage(
                userId,
                "You are already subscribing news from Kaktus operator")

    def removeSubscriber(self, userId):
        """Remove subscriber from list"""
        if self.subscribers.remove(userId):
            self.bot.sendMessage(
                userId,
                "You were removed from subscribing news from Kaktus operator")
        else:
            self.bot.sendMessage(
                userId,
                "You weren't subscribing news from Kaktus operator")

    def showLast(self, userId):
        """Show newest article"""
        if self.article.lastArticle() != '':
            self.bot.sendMessage(userId, self.article.lastArticle())
        else:
            self.bot.sendMessage(userId, "No articles loaded yet.")


class Connection:
    """Loading website source"""

    def loadSource():
        """Load source of page with news"""
        connection = http.client.HTTPSConnection("www.mujkaktus.cz")
        try:
            connection.request("GET", "/novinky")
            response = connection.getresponse()
            if response.status == 200:
                return response.read().decode('utf-8')
            else:
                logging.error("bad response status: " + response.status)
                return None
        except (socket.gaierror, ConnectionResetError) as e:
            logging.error("error while loading data from website: " + e)
        return content


class Telegram:

    def __init__(self, token):
        self.offset = 0
        self.apiUrl = 'https://api.telegram.org/bot' + token + '/'

    def update(self):
        """Load last messages sent to Bot, returns array with new messages"""
        messages = self.sendRequest(
            "getUpdates",
            offset=self.offset,
            timeout=300
        )['result']
        logging.debug('loaded ' + str(len(messages)) + ' messages in update')
        if messages:
            updatedId = messages[-1]['update_id']
            if updatedId != self.offset + 1:
                newMessages = []
                for message in messages:
                    newMessages.append(message)
                # store last update id
                self.offset = updatedId + 1
                logging.debug('new last update id: ' + str(self.offset))
                return newMessages
            else:
                return None

    def sendMessage(self, chatId, message):
        """Send message from bot to specific chat"""
        return self.sendRequest("sendMessage", chat_id=chatId, text=message)

    def sendRequest(self, method, **kwargs):
        """Sends request on Telegram API and returns response"""
        data = urllib.parse.urlencode(kwargs)
        logging.debug('sending request: ' + self.apiUrl + method + '?' + data)
        # TODO: exceptions
        try:
            request = urllib.request.urlopen(self.apiUrl + method + '?' + data)
        except urllib.error.URLError:
            logging.error('It looks like there are issues with connection')
            sys.exit(2)
        response = request.read().decode('utf-8')
        return JSONDecoder().decode(response)


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

    def updateArticle(self, article):
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
    logformat = '%(levelname)s:%(asctime)s (l.%(lineno)d) -- %(message)s'
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
