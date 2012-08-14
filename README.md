     --------------------------------------
    |                                      |
    |    ||     .|';                       |
    |    ||     ||                         |
    |  ''||''  '||'      tinyfeedback      |
    |    ||     ||                         |
    |    `|..' .||.                        |
    |                                      |
     --------------------------------------

**Q**: What on earth ...?

**A**: tinyfeedback is a ridiculously simple way for you to see trends in whatever you are monitoring. You do an HTTP POST to put data in, and you point and click in the web interface to make some graphs. Yay!

<br />
**Q**: What do I need to get started?

**A**:
A *nix machine with redis. The config is currently in two place: you can specify the port the webserver listens on in tinyfeedback/helper.py and you can tweak the logging in bin/tinyfeedback.

To install the dependencies, simply run "pip install -r requirements.txt"

<br />
**Q**: How do I get started?

**A**:
Edit bin/tinyfeedback and tinyfeedback/helper.py to tweak your config as described in the previous Q&A. Make sure redis is running on the machine.

Run bin/tinyfeedback-ctl start. Pause for a moment to reflect on how your life might be changed. Then put some data in to it. Maybe run something like:

`curl -F 'temperature=3000' http://127.0.0.1:8000/data/really_important_server`

Then surf over to http://127.0.0.1:8000 to view your data. To start with, we show you one data point per minute.

Custom graphs can be set up at the /edit URL.

<br />
**Q**: Please tell me you have some helper libraries.

**A**: Of course! Check out these two fine examples:

    '''
    If you're in the middle of a program and are like "Srsly? I have to shell out
    to curl?", then this example is for you.

    Especially useful for monitoring scripts run periodically by cron, then exit.
    '''

    from tinyfeedback.helper import send_once

    if __name__ == '__main__':
        send_once('busy_server', {'cpu_percent': 100, 'memory_free': 0})

<br />

    '''
    This guy will follow a logfile and call parse_line for each line in that file.

    Don't worry about the logfile rotating! This guy will keep on top of it.
    Want to put on your expert pants? Check out the format_data_callback_func arg.
    '''

    from tinyfeedback.helper import tail_monitor

    def parse_line(data, line):
        if 'apple' in line:
            data['apples'] += 1

        elif 'orange' in line:
            data['oranges'] += 1

    if __name__ == '__main__':
        tail_monitor(component='really_important_fruit_server',
                log_filename='/var/log/fruit_server.log',
                line_callback_func=parse_line,
                data_arg={'apples': 0, 'oranges': 0},
                )

<br />
**Q**: How do I get rid of the component created by your really_important_server example?

**A**: Run something like:

`curl -X DELETE http://127.0.0.1/data/really_important_server/temperature`

or just:

`curl -X DELETE http://127.0.0.1/data/really_important_server`
