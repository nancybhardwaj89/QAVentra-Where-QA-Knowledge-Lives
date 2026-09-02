from apscheduler.schedulers.blocking import BlockingScheduler
from auto_ingest import run_sweep
from apscheduler.schedulers.blocking import BlockingScheduler
from auto_ingest import run_sweep
from jira_full_sync import run_full_sync

scheduler = BlockingScheduler()
scheduler.add_job(run_sweep, "interval", hours=1, next_run_time=None)  # runs immediately, then hourly

print("QAVentra auto-ingestion scheduler started. Running every hour.")
run_sweep()  # run once immediately on startup
scheduler.start()



scheduler = BlockingScheduler()
scheduler.add_job(run_sweep, "interval", hours=1)
scheduler.add_job(run_full_sync, "interval", hours=24)

print("QAVentra auto-ingestion scheduler started. Hourly sweeps, daily JIRA full-sync.")
run_sweep()
run_full_sync()
scheduler.start()