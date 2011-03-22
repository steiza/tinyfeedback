import subprocess
import time
import urllib
from twisted.web.client import getPage

import config


def send_once(component, data_dict):
    host = tinyfeedback.config.HOST
    port = tinyfeedback.config.PORT

    url = 'http://%s:%s/data/%s' % (host, port, component)

    try:
        urllib.urlopen(url, data=urllib.urlencode(data_dict))

    except IOError:
        # Failed to send, just keep going
        pass


def send_once_using_twisted(component, data_dict):
    host = tinyfeedback.config.HOST
    port = tinyfeedback.config.PORT

    url = 'http://%s:%s/data/%s' % (host, port, component)

    d = getPage(
        str(url),
        method='POST',
        postdata=urllib.urlencode(data_dict),
        headers={'Content-Type':'application/x-www-form-urlencoded'},
        timeout=35)

    # swallow errors
    d.addErrback(lambda x: None)


def tail_monitor(component, log_filename, line_callback_func, data_arg={},
        format_data_callback_func=None, interval=60):

    host = tinyfeedback.config.HOST
    port = tinyfeedback.config.PORT

    url = 'http://%s:%s/data/%s' % (host, port, component)

    initial_data = data_arg
    current_data = data_arg.copy()

    tail_process = subprocess.Popen(['tail', '--follow=name', log_filename],
            stdout=subprocess.PIPE)

    last_update = time.time()

    while True:
        line = tail_process.stdout.readline()

        if line.strip() == '':
            time.sleep(1)
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
