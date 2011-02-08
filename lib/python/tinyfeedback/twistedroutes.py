import routes
from twisted.web.resource import Resource


class Dispatcher(Resource):
    '''
    Provides routes-like dispatching for twisted.web.server.

    Frequently, it's much easier to describe your website layout using routes
    instead of Resource from twisted.web.resource. This small library lets you
    dispatch with routes in your twisted.web application.

    Usage:

        from twisted.internet import reactor
        from twisted.web.server import Site

        # Create a Controller
        class Controller(object):

            def index(self, request):
                return '<html><body>Hello World!</body></html>'

            def docs(self, request, item):
                return '<html><body>Docs for %s</body></html>' % item.encode('utf8')

            def post_data(self, request):
                return '<html><body>OK</body></html>'

        c = Controller()

        dispatcher = Dispatcher()

        dispatcher.connect(name='index', route='/', controller=c, action='index')

        dispatcher.connect(name='docs', route='/docs/{item}', controller=c,
                action='docs')

        dispatcher.connect(name='data', route='/data', controller=c,
                action='post_data', conditions=dict(method=['POST']))

        factory = Site(dispatcher)
        reactor.listenTCP(8000, factory)
        reactor.run()

    Helpful background information:
    - Python routes: http://routes.groovie.org/
    - Using twisted.web.resources: http://twistedmatrix.com/documents/current/web/howto/web-in-60/dynamic-dispatch.html
    '''

    def __init__(self):
        Resource.__init__(self)

        self.__path = ['']

        self.__controllers = {}
        self.__mapper = routes.Mapper()

    def connect(self, name, route, controller, **kwargs):
        self.__controllers[name] = controller
        self.__mapper.connect(name, route, controller=name, **kwargs)

    def getChild(self, name, request):
        self.__path.append(name)

        return self

    def render_HEAD(self, request):
        return self.__render('HEAD', request)

    def render_GET(self, request):
        return self.__render('GET', request)

    def render_POST(self, request):
        return self.__render('POST', request)

    def render_PUT(self, request):
        return self.__render('PUT', request)

    def render_DELETE(self, request):
        return self.__render('DELETE', request)

    def __render(self, method, request):
        try:
            wsgi_environ = {}
            wsgi_environ['REQUEST_METHOD'] = method
            wsgi_environ['PATH_INFO'] = '/'.join(self.__path)

            result = self.__mapper.match(environ=wsgi_environ)

            handler = None

            if result is not None:
                controller = result.get('controller', None)
                controller = self.__controllers.get(controller)

                if controller is not None:
                    del result['controller']
                    action = result.get('action', None)

                    if action is not None:
                        del result['action']
                        handler = getattr(controller, action, None)

        finally:
            self.__path = ['']

        if handler:
            return handler(request, **result)
        else:
            request.setResponseCode(404)
            return '<html><head><title>404 Not Found</title></head>' \
                    '<body><h1>Not found</h1></body></html>'


if __name__ == '__main__':
    import logging

    import twisted.python.log
    from twisted.internet import reactor
    from twisted.web.server import Site

    # Set up logging
    log = logging.getLogger('twisted_routes')
    log.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log.addHandler(handler)

    observer = twisted.python.log.PythonLoggingObserver(loggerName='twisted_routes')
    observer.start()

    # Create a Controller
    class Controller(object):

        def index(self, request):
            return '<html><body>Hello World!</body></html>'

        def docs(self, request, item):
            return '<html><body>Docs for %s</body></html>' % item.encode('utf8')

        def post_data(self, request):
            return '<html><body>OK</body></html>'

    c = Controller()

    dispatcher = Dispatcher()

    dispatcher.connect(name='index', route='/', controller=c, action='index')

    dispatcher.connect(name='docs', route='/docs/{item}', controller=c,
            action='docs')

    dispatcher.connect(name='data', route='/data', controller=c,
            action='post_data', conditions=dict(method=['POST']))

    factory = Site(dispatcher)
    reactor.listenTCP(8000, factory)
    reactor.run()
