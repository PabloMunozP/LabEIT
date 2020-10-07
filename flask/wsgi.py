from run import app
from flask_apscheduler import APScheduler
# Se importan funciones desde /routines/sched_functions.py
from app.routines.sched_functions import revisar_18_30, revisar_23_59

with app.app_context():
    # ========== Se inicializan las funciones con el objeto de APScheduler =============
    sched = APScheduler()
    sched.add_job(id="revisar_23_59", func=revisar_23_59,
                  trigger='cron', hour=23, minute=59)
    sched.add_job(id="revisar_18_30", func=revisar_18_30,
                  trigger='cron', hour=18, minute=30)
    sched.start()
    # ===================================================================================


if __name__ == "__main__":
    app.run()
