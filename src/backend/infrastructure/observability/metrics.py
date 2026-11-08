from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

class Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.requests = Counter("registration_http_requests_total", "API requests", ["route","method","status"], registry=self.registry)
        self.duration = Histogram("registration_http_request_duration_seconds", "API latency", ["route","method"],
            buckets=(.005,.01,.025,.05,.1,.25,.5,1,2.5,5,10,30), registry=self.registry)
        self.jobs = Counter("registration_jobs_total", "Worker jobs", ["kind","result"], registry=self.registry)
        self.job_duration = Histogram("registration_job_duration_seconds", "Worker execution", ["kind"], registry=self.registry)
