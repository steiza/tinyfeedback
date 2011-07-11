# Here's some curl commands you might want to run:
#   curl -F 'key1=1' -F 'key2=2' http://127.0.0.1:8000/data/component1
#   curl -X DELETE http://127.0.0.1:8000/data/component1/key1

import datetime
import logging
import logging.handlers
import os
import time
import urllib

import mako.template
import mako.lookup
import simplejson
import sqlalchemy
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.static import File

import model
from model import Data
import twistedroutes

log = None

def straighten_out_request(f):
    # The twisted request dictionary return values as lists, this un-does that

    def wrapped_f(*args, **kwargs):
        if 'request' in kwargs:
            request_dict = kwargs['request'].args
        else:
            request_dict = args[1].args

        new_request_dict = {}
        for k, v in request_dict.iteritems():
            new_request_dict[k] = v[0]

        if 'request' in kwargs:
            kwargs['request'].args = new_request_dict
        else:
            args[1].args = new_request_dict

        return f(*args, **kwargs)

    return wrapped_f


class Controller(object):

    def __init__(self, SessionMaker):
        self.__SessionMaker = SessionMaker

        self.timescales = ['6h', '36h', '1w', '1m', '6m']
        self.graph_types = ['line', 'stacked']

        # Set up template lookup directory
        self.__template_lookup = mako.lookup.TemplateLookup(
                directories=[os.path.join(os.path.dirname(__file__),
                    'templates')], input_encoding='utf-8')

    # User-visible pages
    @straighten_out_request
    def get_index(self, request):
        username = request.getCookie('username')

        if 'edit' in request.args:
            edit = request.args['edit']
        else:
            edit = None

        session = self.__SessionMaker()

        rows = session.query(Data.component).group_by(Data.component).order_by(
                Data.component).all()

        session.close()

        keys = [each[0] for each in rows]

        # Look up custom graphs for this user
        if username is not None:
            user_id = model.ensure_user_exists(self.__SessionMaker, username)
            graphs = model.get_graphs(self.__SessionMaker, user_id)

        else:
            user_id = None
            graphs = None

        template = self.__template_lookup.get_template('index.mako')

        return template.render(components=keys, username=username, edit=edit,
                user_id=user_id, graphs=graphs).encode('utf8')

    @straighten_out_request
    def get_component(self, request, component):
        if request.args.get('delete_older_than_a_week', None) is not None:
            model.clean_out_metrics_older_than_a_week(self.__SessionMaker,
                    component)

            request_args = request.args
            del request_args['delete_older_than_a_week']

            redirect = '/view/%s' % component.encode('utf8')
            if len(request_args) > 0:
                redirect += '?%s' % urllib.urlencode(request_args)

            request.setResponseCode(303)
            request.redirect(redirect)
            return ''

        username = request.getCookie('username')

        timescale = request.args.get('ts', '6h')

        if timescale not in self.timescales:
            timescale = '6h'

        metrics = []

        session = self.__SessionMaker()
        rows = session.query(Data).filter(Data.component == component).group_by(
                Data.metric).order_by(Data.metric).all()

        for each in rows:
            data, should_save = each.get_data(timescale)

            if should_save:
                session.merge(each)

            current = data[-1]
            minimum = min(data)
            maximum = max(data)

            metrics.append((each.metric, each.metric.replace('.', '-').replace(
                    ':', '-'), data, current, minimum, maximum))

        session.commit()

        template = self.__template_lookup.get_template('component.mako')

        return template.render(component=component, metrics=metrics,
                username=username, timescale=timescale,
                timescales=self.timescales).encode('utf8')

    @straighten_out_request
    def get_edit(self, request):
        username = request.getCookie('username')

        title = request.args.get('title', '')
        request.args['title'] = title

        if 'delete' in request.args and title != '':
            user_id = model.ensure_user_exists(self.__SessionMaker, username)
            model.remove_graph(self.__SessionMaker, user_id, title)

            request.setResponseCode(303)
            request.redirect('/')
            return ''

        data_sources = model.get_data_sources(self.__SessionMaker)

        for each_metric in data_sources.itervalues():
            each_metric.sort()

        active_components = \
                [each.split('|')[0] for each in request.args if '|' in each]

        graph_type = request.args.get('graph_type', '')

        template = self.__template_lookup.get_template('edit.mako')

        return template.render(kwargs=request.args, data_sources=data_sources,
                active_components=active_components, username=username,
                timescales=self.timescales,
                graph_types=self.graph_types).encode('utf8')

    @straighten_out_request
    def post_edit(self, request):
        username = request.getCookie('username')

        if request.args['title'] == '':
            request.args['error'] = 'no_title'
            redirect = '/edit?%s' % urllib.urlencode(request.args)

            request.setResponseCode(303)
            request.redirect(redirect)
            return ''

        elif len(request.args) == 3:
            request.args['error'] = 'no_fields'
            redirect = '/edit?%s' % urllib.urlencode(request.args)

            request.setResponseCode(303)
            request.redirect(redirect)
            return ''

        user_id = model.ensure_user_exists(self.__SessionMaker, username)
        title = request.args['title']
        timescale = request.args['timescale']
        graph_type = request.args['graph_type']

        keys = request.args.keys()
        index = keys.index('title')
        del keys[index]

        index = keys.index('graph_type')
        del keys[index]

        index = keys.index('timescale')
        del keys[index]

        model.update_graph(self.__SessionMaker, title, user_id, timescale, keys,
                graph_type)

        request.setResponseCode(303)
        request.redirect('/')
        return ''

    @straighten_out_request
    def get_graph(self, request):
        username = request.getCookie('username')

        graph_id = request.args.get('graph_id', '')
        title = request.args.get('title', '')
        graph_type = request.args.get('graph_type', '')
        timescale = request.args.get('timescale', '')

        for each in [graph_id, title, graph_type, timescale]:
            if each == '':
                request.setResponseCode(400)
                return ''

        keys = request.args.keys()

        for each in ['graph_id', 'title', 'graph_type', 'timescale']:
            index = keys.index(each)
            del keys[index]

        graph = model.get_data_for_graph(self.__SessionMaker, graph_id, title,
                graph_type, keys, timescale)

        template = self.__template_lookup.get_template('graph.mako')

        return template.render(username=username, title=title,
                graph_type=graph_type, components=keys, graph=[graph]).encode('utf8')

    # AJAX calls to manipulate user state
    @straighten_out_request
    def post_graph_ordering(self, request):
        log.debug('post graph ordering %s', request.args)

        new_ordering = request.args.get('new_ordering', '')
        user_id = None

        username = request.getCookie('username')
        if username is not None:
            user_id = model.ensure_user_exists(self.__SessionMaker, username)

        if new_ordering == '' or user_id is None:
            request.setResponseCode(400)
            return ''

        new_ordering = simplejson.loads(new_ordering)

        model.update_ordering(self.__SessionMaker, user_id, new_ordering)

        request.setResponseCode(200)
        return ''

    # API for dealing with data
    @straighten_out_request
    def post_data(self, request, component):
        log.debug('posting data for %s', component)

        session = self.__SessionMaker()

        for metric, value in request.args.iteritems():
            # truncate metric to 128 characters
            metric = metric[:128]

            # See if it is in the database
            row = session.query(Data).filter(Data.component == component
                    ).filter(Data.metric == metric).all()

            if len(row) > 0:
                model = row[0]
            else:
                model = Data(component, metric)

            model.update(int(value))
            session.merge(model)

        session.commit()

        return ''

    @straighten_out_request
    def get_data(self, request, component, metric):
        session = self.__SessionMaker()

        # See if it is in the database
        row = session.query(Data).filter(Data.component == component
                ).filter(Data.metric == metric).all()

        if len(row) > 0:
            model = row[0]

        else:
            request.setResponseCode(400)
            request.redirect('/')
            return ''

        ret, should_save = model.get_data()

        if should_save:
            session.merge(model)

        session.commit()

        return str(ret)

    @straighten_out_request
    def delete_data(self, request, component, metric=None):
        session = self.__SessionMaker()

        query = session.query(Data).filter(Data.component == component)

        if metric is not None:
            query = query.filter(Data.metric == metric)

        rows = query.all()

        for each in rows:
            session.delete(each)

        session.commit()

    # Dealing with login
    @straighten_out_request
    def post_login(self, request):
        if request.args.get('username', None) is None:
            request.setResponseCode(400)
            request.redirect('/')
            return ''

        username = request.args['username'].lower()

        # Save the username as a cookie
        current_utc_time = datetime.datetime.utcnow()
        current_utc_time += datetime.timedelta(days=365)
        expires_str = current_utc_time.strftime('%a, %d-%b-%Y %H:%M:%S GMT')

        request.addCookie('username', username, expires=expires_str)

        model.ensure_user_exists(self.__SessionMaker, username)

        referer = request.getHeader('Referer')
        if referer is None:
            referer = '/'

        request.setResponseCode(303)
        request.redirect(referer)
        return ''

    @straighten_out_request
    def get_logout(self, request):
        username = request.getCookie('username')

        request.addCookie('username', username, max_age=0)

        referer = request.getHeader('Referer')
        if referer is None:
            referer = '/'

        request.setResponseCode(303)
        request.redirect(referer)
        return ''


def set_up_server(port, data_store, log_path, log_level):
    global log

    log = logging.getLogger('tinyfeedback')
    level = getattr(logging, log_level, logging.INFO)
    log.setLevel(level)

    handler = logging.StreamHandler()

    if log_path != '':
        dir = os.path.dirname(log_path)
        if not os.path.exists(dir):
            os.makedirs(dir, 0755)

        handler = logging.handlers.RotatingFileHandler(log_path,
                maxBytes=100*1024*1024, backupCount=5)

    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log.addHandler(handler)

    engine = sqlalchemy.create_engine(
            data_store,
            pool_size = 20,
            max_overflow = -1,
            pool_recycle = 1, # Re-open closed connections to db after 1 second
            )

    SessionMaker = model.bind_engine(engine)

    controller = Controller(SessionMaker)

    dispatcher = twistedroutes.Dispatcher()

    # User-visible pages
    dispatcher.connect('get_index', '/', controller=controller,
            action='get_index', conditions=dict(method=['GET']))

    dispatcher.connect('get_component', '/view/:component',
            controller=controller, action='get_component',
            conditions=dict(method=['GET']))

    dispatcher.connect('get_edit', '/edit', controller=controller,
            action='get_edit', conditions=dict(method=['GET']))

    dispatcher.connect('post_edit', '/edit', controller=controller,
            action='post_edit', conditions=dict(method=['POST']))

    dispatcher.connect('get_graph', '/graph', controller=controller,
            action='get_graph', conditions=dict(method=['GET']))

    # AJAX calls to manipulate user state
    dispatcher.connect('post_graph_ordering', '/graph_ordering',
            controller=controller, action='post_graph_ordering',
            conditions=dict(method=['POST']))

    # API for dealing with data
    dispatcher.connect('post_data', '/data/:component', controller=controller,
            action='post_data', conditions=dict(method=['POST']))

    dispatcher.connect('get_data', '/data/:component/:metric',
            controller=controller, action='get_data',
            conditions=dict(method=['GET']))

    dispatcher.connect('delete_data', '/data/:component',
            controller=controller, action='delete_data',
            conditions=dict(method=['DELETE']))

    dispatcher.connect('delete_data', '/data/:component/:metric',
            controller=controller, action='delete_data',
            conditions=dict(method=['DELETE']))

    # Dealing with login
    dispatcher.connect('post_login', '/login', controller=controller,
            action='post_login', conditions=dict(method=['POST']))

    dispatcher.connect('get_logout', '/logout', controller=controller,
            action='get_logout', conditions=dict(method=['GET']))

    static_path = os.path.join(os.path.dirname(__file__), 'static')

    dispatcher.putChild('static', File(static_path))

    factory = Site(dispatcher)
    reactor.listenTCP(port, factory)

    log.info('tiny feedback running on port %d', port)

    reactor.run()


if __name__ == '__main__':
    set_up_server()
