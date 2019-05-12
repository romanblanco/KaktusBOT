import sys
import urllib.parse
import urllib.request

from json import JSONDecoder

import logging

class Telegram:

    def __init__(self):
        self.offset = 0
        try:
            with open('TOKEN', 'r', encoding='utf-8') as token_file:
                token = token_file.read().splitlines()[0]
                self.apiUrl = 'https://api.telegram.org/bot' + token + '/'
        except FileNotFoundError:
            print("\n./TOKEN file containing Telegram token does not exist")
            sys.exit(1)


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
        logging.debug("sending request: " + self.apiUrl + method + "?" + data)
        try:
            request = urllib.request.urlopen(self.apiUrl + method + '?' + data)
            response = request.read().decode('utf-8')
            return JSONDecoder().decode(response)
        except urllib.error.URLError:
            logging.error("It looks like there are issues with connection")
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
                    logging.debug("new last update id: " + str(self.offset))
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
        return self.sendRequest('sendMessage', chat_id=chatId, text=message)
