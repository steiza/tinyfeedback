import platform
import time
import urllib
import urllib2

from twisted.web.client import getPage

import simple_tail

PORT = 8000
HOST = '127.0.0.1'

def send_once(component, data_dict):
    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    try:
        urllib2.urlopen(url, data=urllib.urlencode(data_dict), timeout=5)

    except IOError:
        # Failed to send, just keep going
        pass

def send_once_using_twisted(component, data_dict, timeout=35, ignore_errors=True):
    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    d = getPage(
        str(url),
        method='POST',
        postdata=urllib.urlencode(data_dict),
        headers={'Content-Type':'application/x-www-form-urlencoded'},
        timeout=timeout)

    if ignore_errors:
        d.addErrback(lambda x: None)

    return d

def tail_monitor(component, log_filename, line_callback_func, data_arg={},
        format_data_callback_func=None, interval=60, line_callback_args=None,
        log_subcomponent='monitor'):

    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    if is_osx():
    	arguments = '-F'
   
    else:
    	arguments = '--follow=name'

    # initialize a copy of that initial data
    initial_data = data_arg
    current_data = initial_data.copy()

    tail = simple_tail.SimpleTail(log_filename)

    last_update = time.time()

    while True:
        line = tail.readline()

        # sleep one second if EOF or ''
        if '\0' in line or line.strip() == '':
            time.sleep(1)
        else:
            if line_callback_args:
                line_callback_func(current_data, line, **line_callback_args)
            else:
                line_callback_func(current_data, line)

        current_time = time.time()

        if current_time - last_update >= interval:
	    last_update = current_time

            if format_data_callback_func:
                current_data = format_data_callback_func(current_data)

            # Don't send empty data
            if current_data != {}:
                try:
                    urllib.urlopen(url, data=urllib.urlencode(current_data))

                except IOError:
                    # Failed to send, just keep going
                    pass

                current_data = initial_data.copy()


def is_osx():
    return (platform.system() == 'Darwin')
