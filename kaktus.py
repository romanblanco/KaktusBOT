#!/usr/bin/env python3

import os
import sys
import time
import logging
import signal
from threading import Thread
from bs4 import BeautifulSoup

from connection import Connection
from telegram import Telegram

DEBUG = True
LOADING_TIME = 60*30

class Application:

    def __init__(self):
        self.bot = Telegram()
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
            logging.debug("next iteration of loading thread")
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
        logging.debug("interpreting response: " + str(response))
        for message in response:
            if not 'message' in message.keys():
                continue
            if 'text' in message['message'].keys():
                if message['message']['text'] == '/subscribe':
                    self.addSubscriber(message['message']['from']['id'])
                elif message['message']['text'] == '/unsubscribe':
                    self.removeSubscriber(message['message']['from']['id'])
                elif message['message']['text'] == '/last':
                    self.showLast(message['message']['from']['id'])

    def addSubscriber(self, userId):
        """Add new subscriber to list

        Args:
            - userId -- id of the user who sent the request to be added to the
                        subscribers list
        """
        if self.subscribers.add(userId):
            logging.debug("new subscriber: " + str(userId))
            self.bot.sendMessage(
                userId,
                "You're now subscribing news from Kaktus operator")
        else:
            self.bot.sendMessage(
                userId,
                "Nothing changed")

    def removeSubscriber(self, userId):
        """Remove subscriber from list

        Args:
            - userId -- id of the user who sent the request to be removed
                        from subscribers list
        """
        if self.subscribers.remove(userId):
            logging.debug("one subscriber removed: " + str(userId))
            self.bot.sendMessage(
                userId,
                "You were removed from subscribing news from Kaktus operator")
        else:
            self.bot.sendMessage(
                userId,
                "Nothing changed")

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
