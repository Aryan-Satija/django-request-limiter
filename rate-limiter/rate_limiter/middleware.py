from rate_limiter.conf import rl_settings
from rate_limiter.exceptions import MissingAlgorithmError, InvalidAlgorithmError
from rate_limiter.algorithms.simple_rate_limiter import SimpleRateLimiter
from rate_limiter.algorithms.composite_rate_limiter import CompositeRateLimiter
from rate_limiter.algorithms.token_bucket_rate_limiter import TokenBucketRateLimiter
from rate_limiter.algorithms.leaky_bucket_rate_limiter import LeakyBucketRateLimiter

class RateLimiterMiddleWare:
    def __init__(self, get_response):
        self.next_chain_middleware = get_response
        
    def __call__(self, request):
        algorithm = rl_settings.algorithm
        
        if not algorithm:
            raise MissingAlgorithmError('No algorithm passed')
        
        match algorithm:
            case 'simple':
                return SimpleRateLimiter(self.next_chain_middleware)(request)
            case 'token-bucket':
                return TokenBucketRateLimiter(self.next_chain_middleware)(request)
            case 'leaky-bucket':
                return LeakyBucketRateLimiter(self.next_chain_middleware)(request)
            case 'composite':
                return CompositeRateLimiter(self.next_chain_middleware)(request)
            case _:
                raise InvalidAlgorithmError(algorithm)
                