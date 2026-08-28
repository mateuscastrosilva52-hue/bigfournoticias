Run python update_retrospective.py
Traceback (most recent call last):
  File "/home/runner/work/bigfournoticias/bigfournoticias/update_retrospective.py", line 180, in <module>
    main()
  File "/home/runner/work/bigfournoticias/bigfournoticias/update_retrospective.py", line 175, in main
    retro_html = call_gemini(prompt)
                 ^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/bigfournoticias/bigfournoticias/update_retrospective.py", line 109, in call_gemini
    response.raise_for_status()
  File "/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/requests/models.py", line 1167, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=***
Error: Process completed with exit code 1.
