import platform
import subprocess
import time
import urllib
from twisted.web.client import getPage


PORT = 8000
HOST = '127.0.0.1'


def send_once(component, data_dict):
    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    try:
        urllib.urlopen(url, data=urllib.urlencode(data_dict))

    except IOError:
        # Failed to send, just keep going
        pass


def send_once_using_twisted(component, data_dict):
    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    d = getPage(
            str(url),
            method='POST',
            postdata=urllib.urlencode(data_dict),
            headers={'Content-Type':'application/x-www-form-urlencoded'},
            timeout=10,
            )

    # swallow errors
    d.addErrback(lambda x: None)


def tail_monitor(component, log_filename, line_callback_func, data_arg={},
        format_data_callback_func=None, interval=60):

    url = 'http://%s:%s/data/%s' % (HOST, PORT, component)

    initial_data = data_arg
    current_data = data_arg.copy()

    if is_osx():
        arguments = '-F'
    else:
        arguments = '--follow=name'

    tail_process = subprocess.Popen(['tail', arguments, log_filename],
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


def is_osx():
    return (platform.system() == 'Darwin')
