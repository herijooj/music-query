import queue
import threading
import time
import uuid
import logging

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
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        self._initialized = True

    def add_job(self, job_func, *args, **kwargs):
        """
        Adds a job to the queue.
        :param job_func: The function to execute
        :param args: Positional arguments for the function
        :param kwargs: Keyword arguments for the function
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
        self.queue.put(job)
        return job_id

    def _worker(self):
        logger.info("Background worker started.")
        while self.running:
            try:
                # Wait for a job
                job = self.queue.get(timeout=1)
                
                # Update status
                self.current_job = job
                job['status'] = 'processing'
                logger.info(f"Processing job {job['id']}...")
                
                try:
                    # Execute the job
                    job['func'](*job['args'], **job['kwargs'])
                    job['status'] = 'completed'
                    logger.info(f"Job {job['id']} completed.")
                except Exception as e:
                    job['status'] = 'failed'
                    job['error'] = str(e)
                    logger.error(f"Job {job['id']} failed: {e}")
                
                # Clear current job (keep last status briefly? For now just None)
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
        
        if self.current_job:
            # Create a safe copy for JSON serialization
            job_copy = self.current_job.copy()
            if 'func' in job_copy:
                job_copy['func'] = str(job_copy['func'])
            if 'args' in job_copy:
                job_copy['args'] = str(job_copy['args'])
            if 'kwargs' in job_copy:
                job_copy['kwargs'] = str(job_copy['kwargs'])
            status['current_job'] = job_copy
            
        return status

# Global instance
job_queue = JobQueue()
