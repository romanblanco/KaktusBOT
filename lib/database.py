import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy import exists, and_
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Subscriber(Base):
    __tablename__ = 'subscriber'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer)

    def __repr__(self):
        return f"<Subscriber(id={self.id}, telegram_id={self.telegram_id})>"

class Feed(Base):
    __tablename__ = 'feed'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    text = Column(String)

    def __repr__(self):
        return f"<Feed(id={self.id}, date={self.date}, text='{self.text}')>"

class Delivery(Base):
    __tablename__ = 'delivery'
    id = Column(Integer, primary_key=True)
    message = Column(Integer)
    subscriber = Column(Integer)
    date = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return "<Delivery("\
             + f"id={self.id}, " \
             + f"subscriber={self.subscriber}, " \
             + f"message='{self.message}', " \
             + f"date={self.date}" \
             + ")>"

def dbSession(db_name):
    db = create_engine(db_name)
    Base.metadata.create_all(db)
    Session = sessionmaker(bind=db, expire_on_commit=False)
    return Session()

class Subscribers:
    """Keep users IDs"""

    def exists(self, session, userId):
        find = session.query(exists().where(Subscriber.telegram_id==userId))
        return find.scalar()

    def add(self, userId):
        session = dbSession("sqlite:///data/subscriber.sqlite")
        if self.exists(session, userId):
            session.close()
            return False
        else:
            subscriber = Subscriber(telegram_id=userId)
            session.add(subscriber)
            session.commit()
            session.close()
            return True

    def remove(self, userId):
        session = dbSession("sqlite:///data/subscriber.sqlite")
        if self.exists(session, userId):
            session.query(Subscriber).filter(Subscriber.telegram_id==userId).delete()

            session.commit()
            session.close()
            return True
        else:
            session.close()
            return False

    def all(self):
        session = dbSession("sqlite:///data/subscriber.sqlite")
        return session.query(Subscriber).all()

class Article:

    def __init__(self):
        session = dbSession("sqlite:///data/feed.sqlite")
        query = session.query(Feed).order_by(Feed.date.desc()).first()
        session.close()
        if query is not None:
            self.last = query.text
        else:
            self.last = ''

    def add(self, article):
        """Update article when new one appears

        Args:
            - article -- loaded article to be stored
        Returns:
            - True if the article has been added
            - False if the article is already present
        """
        session = dbSession("sqlite:///data/feed.sqlite")
        if self.exists(session, article):
            session.close()
            return None
        else:
            self.last = article
            article = Feed(text=article)
            session.add(article)
            session.commit()
            session.close()
            return article.id

    def exists(self, session, article):
        find = session.query(exists().where(Feed.text==article))
        return find.scalar()

    def new(self, article):
        """Compare if loaded article is new or not

        Args:
            - article -- loaded article to be compared

        Returns:
            - True if the article is different than the stored one
            - False if the article is the same as the stored one
        """
        return (article != self.last)

class Postman:

    def add(self, message, subscriber):
        session = dbSession("sqlite:///data/delivery.sqlite")
        if self.exists(session, message, subscriber):
            session.close()
            return None
        else:
            delivery = Delivery(message=message, subscriber=subscriber)
            session.add(delivery)
            session.commit()
            session.close()
            return delivery.id

    def exists(self, session, message, subscriber):
        find = session.query(exists().where(and_(Delivery.message==message, Delivery.subscriber==subscriber)))
        return find.scalar()
