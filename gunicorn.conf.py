import multiprocessing
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
timeout = 120
keepalive = 5
accesslog = "/var/www/mailremover/logs/access.log"
errorlog = "/var/www/mailremover/logs/error.log"
loglevel = "info"
proc_name = "mailremover"
