# larpmanager/middleware/log_reverse_calls.py
import logging
from django.urls import reverse, NoReverseMatch

logger = logging.getLogger('django.request')

class ReverseLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Example test: see if reversing happens unexpectedly
            reverse('orga_ci_character_inventory_edit', args=('container3', 1))
        except NoReverseMatch as e:
            logger.debug(f"Reverse call failed: {e}")
        return self.get_response(request)
