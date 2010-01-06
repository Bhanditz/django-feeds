from math import floor, ceil
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache

from celery import conf as celeryconf
from celery.task import Task, PeriodicTask

from djangofeeds.models import Feed
from djangofeeds.importers import FeedImporter

DEFAULT_REFRESH_EVERY = 3 * 60 * 60 # 3 hours
DEFAULT_FEED_LOCK_CACHE_KEY_FMT = "djangofeeds.import_lock.%s"
DEFAULT_FEED_LOCK_EXPIRE = 60 * 3 # lock expires in 3 minutes.


"""
.. data:: REFRESH_EVERY

Interval in seconds between feed refreshes.
Default: 3 hours
Taken from: ``settings.DJANGOFEEDS_REFRESH_EVERY``.

"""
REFRESH_EVERY = getattr(settings, "DJANGOFEEDS_REFRESH_EVERY",
                        DEFAULT_REFRESH_EVERY)


"""
.. data:: REFRESH_EVERY

Prefix for AMQP routing key.
Default: ``celery.conf.AMQP_PUBLISHER_ROUTING_KEY``.
Taken from: ``settings.DJANGOFEEDS_ROUTING_KEY_PREFIX``.

"""
ROUTING_KEY_PREFIX = getattr(settings, "DJANGOFEEDS_ROUTING_KEY_PREFIX",
                             celeryconf.DEFAULT_ROUTING_KEY)

"""
.. data:: FEED_LOCK_CACHE_KEY_FMT

Format used for feed cache lock. Takes one argument: the feeds URL.
Default: "djangofeeds.import_lock.%s"
Taken from: ``settings.DJANGOFEEDS_FEED_LOCK_CACHE_KEY_FMT``.

"""
FEED_LOCK_CACHE_KEY_FMT = getattr(settings,
                            "DJANGOFEEDS_FEED_LOCK_CACHE_KEY_FMT",
                            DEFAULT_FEED_LOCK_CACHE_KEY_FMT)

"""
.. data:: FEED_LOCK_EXPIRE

Time in seconds which after the feed lock expires.
Default: 3 minutes
Taken from: ``settings.DJANGOFEEDS_FEED_LOCK_EXPIRE``.

"""
FEED_LOCK_EXPIRE = getattr(settings,
                    "DJANGOFEEDS_FEED_LOCK_EXPIRE",
                    DEFAULT_FEED_LOCK_EXPIRE)


class RefreshFeedTask(Task):
    """Refresh a djangofeed feed, supports multiprocessing.

    :param feed_url: The URL of the feed to refresh.
    :keyword feed_id: Optional id of the feed, if not specified
        the ``feed_url`` is used instead.

    """
    routing_key = ".".join([ROUTING_KEY_PREFIX, "feedimporter"])
    ignore_result = True

    def run(self, feed_url, feed_id=None, **kwargs):
        feed_id = feed_id or feed_url
        lock_id = FEED_LOCK_CACHE_KEY_FMT % feed_id

        is_locked = lambda: str(cache.get(lock_id)) == "true"
        acquire_lock = lambda: cache.set(lock_id, "true", FEED_LOCK_EXPIRE)
        release_lock = lambda: cache.set(lock_id, "nil", 1)

        logger = self.get_logger(**kwargs)
        logger.info("Importing feed %s" % feed_url)
        if is_locked():
            logger.info("Feed is already being imported by another process.")
            return feed_url

        acquire_lock()
        try:
            importer = FeedImporter(update_on_import=True, logger=logger)
            importer.import_feed(feed_url)
        finally:
            release_lock()

        return feed_url


class RefreshFeedSlice(Task):
    routing_key = ".".join([ROUTING_KEY_PREFIX, "slice"])
    ignore_result = True

    def run(self, start=None, stop=None, step=None, **kwargs):
        feeds = get_feeds(start=start, stop=stop, step=None)

        connection = self.establish_connection()
        try:
            for feed in feeds:
                RefreshFeedTask.apply_async(connection=connection,
                        kwargs={"feed_url": feed.feed_url,
                                "feed_id": feed.pk})
        finally:
            connection.close()


def get_feeds(start=None, stop=None, step=None):
    threshold = datetime.now() - timedelta(seconds=REFRESH_EVERY)
    feeds = Feed.objects.filter(date_last_refresh__lt=threshold)
    if start or stop or step:
        return feeds[slice(start, stop, step)]
    return feeds


class RefreshAllFeeds(PeriodicTask):
    """Periodic Task to refresh all the feeds.

    Splits the feeds into slices, depending how many feeds there are in
    total and how many iterations you want it to run in.

    :keyword iterations: The number of iterations you want the
        work to complete in (default: 4).

    """
    routing_key = ".".join([ROUTING_KEY_PREFIX, "allrefresh"])
    run_every = REFRESH_EVERY
    ignore_result = True

    def run(self, iterations=4, **kwargs):
        logger = self.get_logger(**kwargs)
        total = get_feeds().count()
        win = REFRESH_EVERY * 0.80
        size = ceil(win / iterations) * floor(total / win)
        logger.info("TOTAL: %s WIN: %s SIZE: %s" % (total, win, size))

        for i in xrange(iterations):
            logger.info("APPLYING PAGE: %s (%s -> %s) c:%s" % (
                i, i*size, (i+1)*size, ceil(win/ iterations)*i))
            RefreshFeedSlice.apply_async(args=[(i*size, (i+1)*size)],
                                   countdown=ceil(win / iterations)*i)
