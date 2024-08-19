# gunicorn.conf.py

# Sample Gunicorn configuration with post_fork hook

# Number of worker processes
workers = 2

# Number of threads for handling requests
threads = 2

# Hook for post-fork
# def post_fork(server, worker):
#     from threading import Thread
#     from main import run_at_specific_time  # Import your background task

#     thread = Thread(target=run_at_specific_time, daemon=True)
#     thread.start()