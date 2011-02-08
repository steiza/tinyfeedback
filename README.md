
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
**A**: tinyfeedback is a rediculously simple way for you to see trends in whatever you are monitoring. You do an HTTP POST to put data in, and you point and click in the web interface to make some graphs. Yay!

**Q**: What do I need to get started?
**A**: A *nix machine with mysql; check out lib/python/tinyfeedback/config.py for details.

Q: How do I get started?
A: Run bin/tinyfeedback-ctl start. Pause for a moment to reflect on how your life might be changed. Then put some data in to it. Maybe run something like:

{curl -F 'temperature=3000' http://127.0.0.1:8000/data/really_important_server}

Q: Please tell me you have some helper libraries.
A: Of course! Documentation coming soon!

Q: How do I get rid of your stupid really_important_server example?
A: Run something like:

{curl -X DELETE http://127.0.0.1/really_important_server/temperature}

or just:

{curl -X DELETE http://127.0.0.1/really_important_server}
