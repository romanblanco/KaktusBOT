import http.client
import logging

class Connection:
    """Loading website source"""

    def loadSource():
        """Load source of page with news

        Returns:
            - Page source code, if request succeeds
            - None if request fails
        """
        connection = http.client.HTTPSConnection('www.mujkaktus.cz')
        try:
            connection.request('GET', '/novinky')
            response = connection.getresponse()
            if response.status == 200:
                return response.read().decode('utf-8')
            else:
                logging.error("bad response status: " + str(response.status))
                return None
        except Exception as e:
            logging.error("error while loading data from website: ", e)
            return None
