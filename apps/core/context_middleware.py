class BaseTemplateMiddleware:
    """Middleware to optionally switch base template for HTMX requests"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.headers.get('HX-Request'):
            request.base_template = 'core/modal_base.html'
            request.is_htmx = True
        else:
            request.base_template = 'base.html'
            request.is_htmx = False
        
        response = self.get_response(request)
        return response
