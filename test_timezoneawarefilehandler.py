import pytz
import time
from datetime import datetime, timedelta
import os
from timzeoneawarefilehandler import TimezoneAwareTimedRotatingFileHandler

@pytest.fixture
def nopytestLog():    # Remove any generated log rollover files
    yield
    ptls = [f for f in os.listdir('.') if f.startswith('pytestLog.')]
    for ptl in ptls:
        try:
            os.remove(ptl)
        except Exception:
            pass
        
@pytest.mark.parametrize("zone", ["America/Chicago", "America/New_York", "America/Los_Angeles", "UTC"])
def test_timezone_logger(monkeypatch, nopytestLog, zone):
    central = pytz.timezone(zone)
    handler = TimedRotatingFileHandler('test', when='midnight', utc=True)
    new_handler = TimezoneAwareTimedRotatingFileHandler('pytestLog', when='midnight', utc=True, tzinfo=None)
    central_handler = TimezoneAwareTimedRotatingFileHandler('pytestLog', when='midnight',
                                                        backupCount=1, tzinfo=central)
    central_4pm_handler = TimezoneAwareTimedRotatingFileHandler('pytestLog', when='midnight',
                                            tzinfo=central, atTime=dt_time(16, 0, 0))
    central_monday_handler = TimezoneAwareTimedRotatingFileHandler('pytestLog', when='W0',
                                            tzinfo=central)
    central_monday_5pm_handler = TimezoneAwareTimedRotatingFileHandler('pytestLog', when='W0',
                                            tzinfo=central, atTime=dt_time(17, 0, 0))

    _DAY_PLUS_HOUR_MINUTE = 24 * 60 * 60 + 60 * 60 + 60
    
    testTime = central.localize(datetime(year=2020, month=2, day=1, hour=0)).timestamp()
    times = [testTime + i * _DAY_PLUS_HOUR_MINUTE for i in range(24)]
    zeros = [0 for i in range(24)]
    mar_7 = central.localize(datetime(year=2020, month=3, day=7, hour=8)).timestamp()
    mar_8 = central.localize(datetime(year=2020, month=3, day=8, hour=0)).timestamp()
    oct_31_dt_naive = datetime(year=2020, month=10, day=31, hour=4)
    oct_31 = central.localize(oct_31_dt_naive).timestamp()
    nov_1 = central.localize(datetime(year=2020, month=11, day=1, hour=0)).timestamp()
    dec_31 = central.localize(datetime(year=2020, month=12, day=31, hour=23, minute=59)).timestamp()
    
    whats_the_time = time.time()
    def mock_time():
        nonlocal whats_the_time
        return whats_the_time
    
    monkeypatch.setattr(time, 'time', mock_time)

    times = (*times, mar_7, mar_8, oct_31, nov_1, dec_31)
    tadjm = [*zeros, 0, -3600, 0, 3600, 0]
    if central.dst(oct_31_dt_naive) == timedelta(0):   # This timezone doesn't have DST
        tadjm[-2] = 0
        tadjm[-4] = 0
    for ndx, tm in enumerate(times):
        assert handler.computeRollover(tm) == new_handler.computeRollover(tm)
        roll = central_handler.computeRollover(tm)
        og = pytz.utc.localize(datetime.utcfromtimestamp(tm))
        og = central.normalize(og.astimezone(central))
        
        dt = pytz.utc.localize(datetime.utcfromtimestamp(roll))
        dt = central.normalize(dt.astimezone(central))

        #print(og, dt)
        assert dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0
        assert dt > og
        assert (dt - og) <= timedelta(days=1, hours=1)
        assert central_handler._tz_dst_adjust(tm, roll) - roll == tadjm[ndx]
        
        roll = central_4pm_handler.computeRollover(tm)
        dt = pytz.utc.localize(datetime.utcfromtimestamp(roll))
        dt = central.normalize(dt.astimezone(central))
        assert dt.hour == 16 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0
        assert dt > og
        assert (dt - og) <= timedelta(days=1, hours=17)
             
        roll = central_monday_handler.computeRollover(tm)
        dt = pytz.utc.localize(datetime.utcfromtimestamp(roll))
        dt = central.normalize(dt.astimezone(central))
        #print(dt, dt.weekday())
        assert dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0
        assert dt > og
        assert dt.weekday() == 1    # Tuesday
        
        roll = central_monday_5pm_handler.computeRollover(tm)
        dt = pytz.utc.localize(datetime.utcfromtimestamp(roll))
        dt = central.normalize(dt.astimezone(central))
        #print("og, dt =", og, dt)
        assert dt.hour == 17 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0
        assert dt > og
        assert dt.weekday() == 0    # Monday
        
        whats_the_time = tm
        central_handler.doRollover()
        roll = central_handler.rolloverAt
        dt = pytz.utc.localize(datetime.utcfromtimestamp(roll))
        dt = central.normalize(dt.astimezone(central))
        assert dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0
        assert dt > og
        assert (dt - og) <= timedelta(days=1, hours=1)
