import os
import time
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
import pytz
from logging.handlers import TimedRotatingFileHandler, _MIDNIGHT
​
class TimezoneAwareTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Handler for logging to a file, rotating the log file at certain timed
    intervals.
    If backupCount is > 0, when rollover is done, no more than backupCount
    files are kept - the oldest ones are deleted.
    
    Allows you to roll the logs at Midnight in any timezone independent of the server's localtime zone.
    tzinfo specifies the time zone and must be a pytz, and is only obeyed if utc=True.
    """
    def __init__(self, filename, when='h', interval=1, backupCount=0,
                 encoding=None, delay=False, utc=False, atTime=None,
                 errors=None, tzinfo=None):
        self.tzinfo = tzinfo
        if tzinfo is not None:
            utc = True
        TimedRotatingFileHandler.__init__(self, filename, when=when, encoding=encoding, backupCount=backupCount,
                                     delay=delay, utc=utc, atTime=atTime, #errors=errors)  in python 3.9 only
                                         )
        # Current 'when' events supported:
        # S - Seconds
        # M - Minutes
        # H - Hours
        # D - Days
        # midnight - roll over at midnight
        # W{0-6} - roll over on a certain day; 0 - Monday
        #
        # Case of the 'when' specifier is not important; lower or upper case
        # will work.
​
    def _tz_dst_adjust(self, currentTime, newRolloverAt):
        """If currentTime and newRolloverAt spans a DST adjustment, perform that adjustment to
        newRolloverAt"""
        cur_dt = pytz.utc.localize(datetime.utcfromtimestamp(currentTime))
        cur_dt = cur_dt.astimezone(self.tzinfo)
        dstNow = cur_dt.timetuple()[-1]
        tz_dt = pytz.utc.localize(datetime.utcfromtimestamp(newRolloverAt))
        tz_dt = tz_dt.astimezone(self.tzinfo)
        dstAtRollover = tz_dt.timetuple()[-1]
        #print(cur_dt, tz_dt, dstNow, dstAtRollover)
        if dstNow != dstAtRollover:
            addend = 3600
            if not dstNow:
                addend = -3600
            newRolloverAt += addend
        return newRolloverAt
    
    def roundUpToTime(self, dt, tm):
        """Given a datetime in dt, round it up to the time given by tm using self.tzinfo for all.
        dt must be already in self.tzinfo and normalized"""
        naive_dt = dt.replace(tzinfo=None)
        if naive_dt.hour == 0:
            naive_dt = naive_dt.replace(second=1)    # Ensure we round up if given midnight
        adj_naive_dt = datetime.combine(naive_dt, tm)
        adj_naive_dt = adj_naive_dt + timedelta(days=adj_naive_dt < naive_dt)
        return self.tzinfo.localize(adj_naive_dt, is_dst=None)   
    
    def computeRollover(self, currentTime):
        """
        Work out the rollover time based on the specified time.
        """
        result = currentTime + self.interval
        # If we are rolling over at midnight or weekly, then the interval is already known.
        # What we need to figure out is WHEN the next interval is.  In other words,
        # if you are rolling over at midnight, then your base interval is 1 day,
        # but you want to start that one day clock at midnight, not now.  So, we
        # have to fudge the rolloverAt value in order to trigger the first rollover
        # at the right time.  After that, the regular interval will take care of
        # the rest.  Note that this code doesn't care about leap seconds. :)
        if self.when == 'MIDNIGHT' or self.when.startswith('W'):
            # This could be done with less code, but I wanted it to be clear
            if self.utc:
                t = time.gmtime(currentTime)
            else:
                t = time.localtime(currentTime)
            currentHour = t[3]
            currentMinute = t[4]
            currentSecond = t[5]
            currentDay = t[6]
            # r is the number of seconds left between now and the next rotation
            if self.atTime is None:
                rotate_ts = _MIDNIGHT
            else:
                rotate_ts = ((self.atTime.hour * 60 + self.atTime.minute)*60 +
                    self.atTime.second)
                
            if self.tzinfo is not None and self.utc:      # Handle the timezone
                #print(f'currentTime = {currentHour} {currentMinute} {currentSecond}')
                tz_dt_utc = pytz.utc.localize(datetime.utcfromtimestamp(currentTime))
                tz_dt = self.tzinfo.normalize(tz_dt_utc.astimezone(self.tzinfo))
                currentDay = tz_dt.weekday()
                atTime = dt_time(0, 0, 0)
                if self.atTime is not None:
                    atTime = self.atTime
                
                rotate_dt = self.roundUpToTime(tz_dt, atTime)
                #print("tz_dt, rotate_dt = ", tz_dt, rotate_dt)
                rotate_dt_utc = pytz.utc.normalize(rotate_dt.astimezone(pytz.utc))    # convert back to utc
                #print("tz_dt_utc, rotate_dt_utc = ", tz_dt_utc, rotate_dt_utc)
                delta = rotate_dt_utc - tz_dt_utc
                delta = int(delta.total_seconds())
                rotate_ts = delta + ((currentHour * 60 + currentMinute) * 60 + currentSecond)
                
                #print(f'delta = {delta}, rotate_ts = {rotate_ts}')
                if self.when.startswith('W') and self.atTime is not None:
                    #currentDay = time.gmtime(currentTime + delta)[6]    # Recompute it for the result time
                    currentDay = rotate_dt.weekday()    # Recompute it for the result time in proper timezone
​
            r = rotate_ts - ((currentHour * 60 + currentMinute) * 60 +
                currentSecond)
            if r < 0:
                # Rotate time is before the current time (for example when
                # self.rotateAt is 13:45 and it now 14:15), rotation is
                # tomorrow.
                r += _MIDNIGHT
                currentDay = (currentDay + 1) % 7
            #print(f'r = {r}')
            result = currentTime + r
            # If we are rolling over on a certain day, add in the number of days until
            # the next rollover, but offset by 1 since we just calculated the time
            # until the next day starts.  There are three cases:
            # Case 1) The day to rollover is today; in this case, do nothing
            # Case 2) The day to rollover is further in the interval (i.e., today is
            #         day 2 (Wednesday) and rollover is on day 6 (Sunday).  Days to
            #         next rollover is simply 6 - 2 - 1, or 3.
            # Case 3) The day to rollover is behind us in the interval (i.e., today
            #         is day 5 (Saturday) and rollover is on day 3 (Thursday).
            #         Days to rollover is 6 - 5 + 3, or 4.  In this case, it's the
            #         number of days left in the current week (1) plus the number
            #         of days in the next week until the rollover day (3).
            # The calculations described in 2) and 3) above need to have a day added.
            # This is because the above time calculation takes us to midnight on this
            # day, i.e. the start of the next day.
            if self.when.startswith('W'):
                day = currentDay
                dow = self.dayOfWeek
                if self.atTime is None:
                    day = (currentDay + 1) % 7
                    dow = (self.dayOfWeek + 1) % 7    # We really rollover at midnight on the next day
                if day != dow:
                    if day < dow:
                        daysToWait = dow - day
                    else:
                        daysToWait = 6 - day + dow + 1
                    #print(f'day = {day}, dow = {dow}, daysToWait = {daysToWait}')
                    newRolloverAt = result + (daysToWait * (60 * 60 * 24))
                    if not self.utc:
                        dstNow = t[-1]
                        dstAtRollover = time.localtime(newRolloverAt)[-1]
                        if dstNow != dstAtRollover:
                            if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                                addend = -3600
                            else:           # DST bows out before next rollover, so we need to add an hour
                                addend = 3600
                            newRolloverAt += addend
                    elif self.tzinfo is not None:
                        newRolloverAt = self._tz_dst_adjust(result, newRolloverAt)
                    result = newRolloverAt
        return result
​
    def doRollover(self):
        """
        do a rollover; in this case, a date/time stamp is appended to the filename
        when the rollover happens.  However, you want the file to be named for the
        start of the interval, not the current time.  If there is a backup count,
        then we have to get a list of matching filenames, sort them and remove
        the one with the oldest suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)
        dfn = self.rotation_filename(self.baseFilename + "." +
                                     time.strftime(self.suffix, timeTuple))
        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        #If DST changes and midnight or weekly rollover, adjust for this.
#       This code commented out because computeRollover already handles this for us:
#       if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and self.utc and self.tzinfo is not None:
#           newRolloverAt = self._tz_dst_adjust(currentTime, newRolloverAt)
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    addend = -3600
                else:           # DST bows out before next rollover, so we need to add an hour
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt
