# TimezoneAwareTimedRotatingFileHandler
For python logging, a TimedRotatingFileHandler that obeys time zones.  If the added tzinfo parameter is specified (as a pytz.timezone), the utc parameter is ignored.  The atTime parameter can be specified and is obeyed in the specified time zone.  The tzinfo parameter works for "when" specified as "midnight" or any of the "Wn" weekly settings.

Usage:

    import pytz
    from timezoneawarefilehandler import TimezoneAwareTimedRotatingFileHandler
    
    central = pytz.timezone("America/Chicago")
    # Rotate the log daily at Midnight Central Time:
    central_handler = TimezoneAwareTimedRotatingFileHandler('mylog', when='midnight',
                                                        backupCount=30, tzinfo=central)
