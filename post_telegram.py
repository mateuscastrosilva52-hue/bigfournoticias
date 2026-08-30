atualização-notícias
fracassado agoraem 11s
Registros de pesquisa
1s
0s
0s
3s
2s
2s
1s
Run python post_telegram.py --mode news
Traceback (most recent call last):
  File "/home/runner/work/bigfournoticias/bigfournoticias/post_telegram.py", line 113, in <module>
    main()
  File "/home/runner/work/bigfournoticias/bigfournoticias/post_telegram.py", line 109, in main
    send_message(message)
  File "/home/runner/work/bigfournoticias/bigfournoticias/post_telegram.py", line 73, in send_message
    response.raise_for_status()
  File "/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/site-packages/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 400 Client Error: Bad Request for url: https://api.telegram.org/bot***/sendMessage
Error: Process completed with exit code 1.
0s
0s
