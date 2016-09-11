#!/usr/bin/env python3

import os
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
from bs4 import BeautifulSoup

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
                soup = BeautifulSoup(source, 'html.parser')
                news = [(article.h3.get_text(),
                         article.p.get_text()) for article in soup.find_all(
                           'div',
                           class_='journal-content-article')]
            else:
                news = []
            if len(news):
                header, paragraph = news[0]
                loadedArticle = header + ' — ' + paragraph
                logging.debug("loaded article: \"" + loadedArticle + "\"")
                if self.article.new(loadedArticle):
                    self.article.updateArticle(loadedArticle)
                    for subscriber in self.subscribers.subscribersList:
                        self.bot.sendMessage(int(subscriber), loadedArticle)
            time.sleep(LOADING_TIME)

    def receivingThread(self):
        """Thread that handles receiving messages"""
        while True:
            logging.debug("next iteration of receiving thread")
            response = self.bot.receiveMessages()
            if response is not None:
                self.interpret(response)

    def interpret(self, response):
        """From response recognize which action should be done

        Args:
            - response -- Array of messages sent to the Bot
        """
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
        """Add new subscriber to list

        Args:
            - userId -- id of the user who sent the request to be added to the
                        subscribers list
        """
        if self.subscribers.add(userId):
            self.bot.sendMessage(
                userId,
                "You're now subscribing news from Kaktus operator")
        else:
            self.bot.sendMessage(
                userId,
                "You are already subscribing news from Kaktus operator")

    def removeSubscriber(self, userId):
        """Remove subscriber from list

        Args:
            - userId -- id of the user who sent the request to be removed
                        from subscribers list
        """
        if self.subscribers.remove(userId):
            self.bot.sendMessage(
                userId,
                "You were removed from subscribing news from Kaktus operator")
        else:
            self.bot.sendMessage(
                userId,
                "You weren't subscribing news from Kaktus operator")

    def showLast(self, userId):
        """Sends newest article to user who sent the request

        Args:
            - userId -- id of the user who sent the request to show last
                        article
        """
        if self.article.last != '':
            self.bot.sendMessage(userId, self.article.last)
        else:
            self.bot.sendMessage(userId, "No articles loaded yet.")


class Connection:
    """Loading website source"""

    def loadSource():
        """Load source of page with news

        Returns:
            - Page source code, if request succeeds
            - None if request fails
        """
        connection = http.client.HTTPSConnection("www.mujkaktus.cz")
        try:
            connection.request("GET", "/novinky")
            response = connection.getresponse()
            if response.status == 200:
                return response.read().decode('utf-8')
            else:
                logging.error("bad response status: " + str(response.status))
                return None
        except (socket.gaierror, ConnectionResetError) as e:
            logging.error("error while loading data from website: " + e)
            return None


class Telegram:

    def __init__(self, token):
        self.offset = 0
        self.apiUrl = 'https://api.telegram.org/bot' + token + '/'

    def sendRequest(self, method, **kwargs):
        """Sends request on Telegram API and returns response

        Args:
            - method -- request method
            - kwargs -- request specific arguments

        Returns:
            - JSON Object with messages, if request succeeds
            - None, if request fails
        """
        data = urllib.parse.urlencode(kwargs)
        logging.debug('sending request: ' + self.apiUrl + method + '?' + data)
        try:
            request = urllib.request.urlopen(self.apiUrl + method + '?' + data)
            response = request.read().decode('utf-8')
            return JSONDecoder().decode(response)
        except urllib.error.URLError:
            logging.error('It looks like there are issues with connection')
            return None

    def receiveMessages(self):
        """Load last messages sent to Bot, returns array with new messages

        Returns:
            - Array with new messages if request succeeds
            - None if request fails or if there is no new message
        """
        requestResult = self.sendRequest(
            'getUpdates',
            offset=self.offset,
            timeout=300)
        if requestResult is not None:
            messages = requestResult['result']
            logging.debug('loaded ' + str(len(messages)) + ' messages')
            if messages:
                updatedId = messages[-1]['update_id']
                if updatedId != self.offset + 1:
                    newMessages = []
                    for message in messages:
                        newMessages.append(message)
                    # store last update id as next offset
                    self.offset = updatedId + 1
                    logging.debug('new last update id: ' + str(self.offset))
                    return newMessages
                else:
                    return None
        else:
            return None

    def sendMessage(self, chatId, message):
        """Send message from bot to specific chat

        Args:
            - chatId -- message receivers ID
            - message -- message sent to the reciever
        """
        return self.sendRequest("sendMessage", chat_id=chatId, text=message)


class Subscribers:
    """Keep users IDs"""

    def __init__(self):
        """Load subscribers IDs from file or start a new list"""
        if os.path.isfile('subscribers.lst'):
            with open('subscribers.lst', 'r') as subscribersFile:
                self.subscribersList = subscribersFile.read().splitlines()
        else:
            self.subscribersList = []

    def add(self, userId):
        """Add users ID to list of subscribers

        Args:
            - userId -- new subscribers ID

        Returns:
            - True if the user was added to subscribers list
            - False if user is already a subscriber
        """
        if str(userId) not in self.subscribersList:
            self.subscribersList.append(str(userId))
            logging.debug("new subscriber: " + str(self.subscribersList))
            self.updateSubscribersFile()
            return True
        else:
            return False

    def remove(self, userId):
        """Remove users ID from list of subscribers

        Args:
            - userId -- leaving subscribers ID

        Returns:
            - True if the user was removed from subscribers list
            - False if user was not subscriber
        """
        if str(userId) in self.subscribersList:
            self.subscribersList.remove(str(userId))
            logging.debug(
              "one subscriber removed: " +
              str(self.subscribersList))
            self.updateSubscribersFile()
            return True
        else:
            return False

    def updateSubscribersFile(self):
        """Write subscribers IDs to file on every change"""
        subscribersFile = open('subscribers.lst', 'w')
        for id in self.subscribersList:
            subscribersFile.write('%s\n' % id)


class Article:
    """Load and return articles from website"""

    def __init__(self):
        self.last = ''

    def updateArticle(self, article):
        """Update article when new one appears

        Args:
            - article -- loaded article to be stored
        """
        self.last = article

    def new(self, article):
        """Compare if loaded article is new or not

        Args:
            - article -- loaded article to be compared

        Returns:
            - True if the article is different than the stored one
            - False if the article is the same as the stored one
        """
        return (article != self.last)


class LogFilter:
    """Filtering log messages with higher level"""

    def __init__(self, level):
        self.__level = level

    def filter(self, logRecord):
        return logRecord.levelno <= self.__level


def signal_handler(signal, frame):
    """Exits script after catching SIGINT signal"""
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
