import time
from collections import defaultdict
from core.response import Response

class RateLimiter:
    """
    Simple In-Memory Rate Limiter
    Format: { ip: [timestamp1, timestamp2, ...] }
    """
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, ip):
        now = time.time()
        # Remove old timestamps outside the window
        self.requests[ip] = [
            ts for ts in self.requests[ip] 
            if now - ts < self.window_seconds
        ]

        if len(self.requests[ip]) >= self.max_requests:
            return False
        
        self.requests[ip].append(now)
        return True

def rate_limit_middleware(max_requests=100, window_seconds=60):
    """
    Middleware Factory for Rate Limiting
    Usage: router.use(rate_limit_middleware(max_requests=50))
    """
    limiter = RateLimiter(max_requests, window_seconds)

    def middleware(request, next_handler):
        ip = request.ip or '127.0.0.1'
        
        if not limiter.is_allowed(ip):
            return Response(
                body={"error": "Too Many Requests", "message": "Rate limit exceeded. Try again later."},
                status=429,
                headers={"Content-Type": "application/json"}
            )
        
        return next_handler(request)

    return middleware
