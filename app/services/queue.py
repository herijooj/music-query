import queue
import threading
import time
import uuid
import logging
from ..config import Config

logger = logging.getLogger(__name__)

class JobQueue:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobQueue, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.queue = queue.Queue()
        self.current_job = None
        self.running = True
        self._lock = threading.Lock()
        self._statuses = {}
        self.current_jobs = set()

        self._max_workers = max(1, int(getattr(Config, 'MAX_CONCURRENT_DOWNLOADS', 1)))
        self.worker_threads = []
        for i in range(self._max_workers):
            t = threading.Thread(target=self._worker, daemon=True, name=f"job-worker-{i+1}")
            t.start()
            self.worker_threads.append(t)

        self._initialized = True

        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()

    def _cleanup_loop(self):
        """Periodically clean up old job statuses."""
        while self.running:
            time.sleep(600)  # Run every 10 minutes
            self._cleanup_old_statuses()

    def _cleanup_old_statuses(self, max_age_seconds=3600):
        """Remove statuses older than max_age_seconds."""
        now = time.time()
        expired = []
        with self._lock:
            for jid, entry in self._statuses.items():
                timestamp = entry.get('timestamp', 0)
                if now - timestamp > max_age_seconds:
                    expired.append(jid)
            for jid in expired:
                del self._statuses[jid]
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired job statuses")

    def add_job(self, job_func, *args, include_job_id=False, **kwargs):
        """
        Adds a job to the queue.
        :param job_func: The function to execute
        :param args: Positional arguments for the function
        :param kwargs: Keyword arguments for the function
        :param include_job_id: If True, passes job_id to job_func as kwarg
        :return: job_id
        """
        job_id = str(uuid.uuid4())
        job = {
            'id': job_id,
            'func': job_func,
            'args': args,
            'kwargs': kwargs,
            'status': 'pending',
            'timestamp': time.time()
        }
        job['include_job_id'] = include_job_id
        self.queue.put(job)
        self._update_status(job_id, state='queued', stage='queued')
        return job_id

    def _worker(self):
        logger.info("Background worker started.")
        while self.running:
            try:
                # Wait for a job
                job = self.queue.get(timeout=1)
                
                # Update status
                with self._lock:
                    self.current_job = job
                    self.current_jobs.add(job['id'])
                    job['status'] = 'processing'
                logger.info(f"Processing job {job['id']}...")
                self._update_status(job['id'], state='processing', stage='starting')
                
                try:
                    # Execute the job
                    if job.get('include_job_id'):
                        job['func'](*job['args'], job_id=job['id'], **job['kwargs'])
                    else:
                        job['func'](*job['args'], **job['kwargs'])
                    job['status'] = 'completed'
                    self._update_status(job['id'], state='completed', stage='done')
                    logger.info(f"Job {job['id']} completed.")
                except Exception as e:
                    job['status'] = 'failed'
                    job['error'] = str(e)
                    self._update_status(job['id'], state='failed', stage='failed', error=str(e))
                    logger.error(f"Job {job['id']} failed: {e}")
                
                # Clear current job (keep last status briefly? For now just None)
                with self._lock:
                    self.current_jobs.discard(job['id'])
                    self.current_job = None
                self.queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def get_status(self):
        status = {
            'queue_size': self.queue.qsize(),
            'current_job': None
        }
        
        with self._lock:
            current_ids = list(self.current_jobs)
            current_statuses = []
            for jid in current_ids:
                entry = self._statuses.get(jid)
                if entry:
                    current_statuses.append({**entry, 'id': jid})
            if current_statuses:
                status['current_job'] = current_statuses[0]
                status['current_jobs'] = current_statuses
            
        return status

    def _update_status(self, job_id, **kwargs):
        with self._lock:
            entry = self._statuses.get(job_id, {})
            entry.update(kwargs)
            self._statuses[job_id] = entry

    def update_job_status(self, job_id, **kwargs):
        self._update_status(job_id, **kwargs)

    def get_job_status(self, job_id):
        with self._lock:
            return self._statuses.get(job_id)

    def shutdown(self, timeout=5):
        """Gracefully shut down all worker threads."""
        logger.info("Shutting down job queue...")
        self.running = False
        for t in self.worker_threads:
            t.join(timeout)
        logger.info("Job queue shut down complete.")

# Global instance
job_queue = JobQueue()
