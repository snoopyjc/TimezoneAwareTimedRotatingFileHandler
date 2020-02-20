# TimezoneAwareTimedRotatingFileHandler
For python logging, a TimedRotatingFileHandler that obeys time zones

Usage:

    import pytz
    from timezoneawarefilehandler import TimezoneAwareTimedRotatingFileHandler
    central = pytz.timezone("America/Chicago")
    central_handler = TimezoneAwareTimedRotatingFileHandler('mylog', when='midnight', utc=True, 
                                                        backupCount=30, tzinfo=central)
