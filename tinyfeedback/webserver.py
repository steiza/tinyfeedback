# Here's some curl commands you might want to run:
#   curl -F 'key1=1' -F 'key2=2' http://127.0.0.1:8000/data/component1
#   curl -X DELETE http://127.0.0.1:8000/data/component1/key1

import datetime
import cgi
import logging
import logging.handlers
import os
import time
import urllib
import re

import mako.template
import mako.lookup
import simplejson
import sqlalchemy
from twisted.internet import defer, reactor, threads
from twisted.internet.task import deferLater
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.static import File
import txroutes

import redis_model


def straighten_out_request(f):
    # The twisted request dictionary return values as lists, this un-does that

    def wrapped_f(*args, **kwargs):
        start = time.time()

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

        ret = f(*args, **kwargs)

        took = time.time() - start

        if took > 0.5:
            args[0]._log.warn('%s took %f to complete', f, took)

        return ret

    return wrapped_f


class Controller(object):

    def __init__(self, redis_model_data, redis_model_graph, log):
        self.__redis_model_data = redis_model_data
        self.__redis_model_graph = redis_model_graph
        self._log = log

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

        self.__finish_get_index(request, username, edit)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_index(self, request, username, edit):
        components = yield self.__redis_model_data.get_components()

        # Look up custom graphs for this user
        if username is not None:
            graphs = yield self.__redis_model_graph.get_graphs(username)
        else:
            graphs = {}

        graph_data = [None] * len(graphs)

        for title, each_graph in graphs.iteritems():
            graph_data[each_graph['ordering']] = yield self.__get_graph_details(
                    title, each_graph)

        template = self.__template_lookup.get_template('index.mako')

        ret = template.render(components=components, username=username,
                edit=edit, graphs=graph_data, cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

    @straighten_out_request
    def get_component(self, request, component):
        if request.args.get('delete_older_than_a_week', None) is not None:
            self.__redis_model_data.delete_metrics_older_than_a_week(component)

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

        self.__finish_get_component(request, component, username, timescale)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_component(self, request, component, username, timescale):
        metrics = yield self.__redis_model_data.get_metrics(component)
        metric_data = []

        for each_metric in metrics:
            data = yield self.__redis_model_data.get_data(component,
                    each_metric, timescale)

            # HACK: if the last value is 0, set it the previous value so sparkline doesn't drop off to 0
            if data[-1] == 0:
                data[-1] = data[-2]

            current = data[-1]
            minimum = min(data)
            maximum = max(data)

            metric_data.append((each_metric, data, current, minimum, maximum))

        template = self.__template_lookup.get_template('component.mako')

        ret = template.render(component=component, metrics=metric_data,
                username=username, timescale=timescale,
                timescales=self.timescales, cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

    @straighten_out_request
    def get_edit(self, request):
        username = request.getCookie('username')

        title = request.args.get('title', '')
        title = urllib.unquote_plus(title.replace('$2F', '%2F'))
        request.args['title'] = title

        if 'delete' in request.args and title != '':
            self.__redis_model_graph.remove_graph(username, title)

            request.setResponseCode(303)
            request.redirect('/')
            return ''

        self.__finish_get_edit(request, username, title)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_edit(self, request, username, title):
        data_sources = {}

        components = yield self.__redis_model_data.get_components()

        for each_component in components:
            metrics = yield self.__redis_model_data.get_metrics(each_component)
            metrics.sort()

            data_sources[each_component] = metrics

        graphs = yield self.__redis_model_graph.get_graphs(username)
        if title and title in graphs:
            fields = graphs[title]['fields']
            active_components = [each.split('|')[0] for each in fields]

        else:
            fields = []
            active_components = []

        graph_type = request.args.get('graph_type', '')

        template = self.__template_lookup.get_template('edit.mako')

        ret = template.render(kwargs=request.args, fields=fields,
                data_sources=data_sources, active_components=active_components,
                username=username, timescales=self.timescales,
                graph_types=self.graph_types, cgi=cgi).encode('utf8')

        request.write(ret)
        request.finish()

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

        # Make sure any wildcards are correctly formatted
        for each_key in keys:
            if '*' in each_key and '|' not in each_key:
                request.args['error'] = 'bad_wildcard_filter'
                redirect = '/edit?%s' % urllib.urlencode(request.args)

                request.setResponseCode(303)
                request.redirect(redirect)
                return ''

        self.__finish_post_edit(request, username, title, timescale, keys,
                graph_type)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_post_edit(self, request, username, title, timescale, keys,
            graph_type):

        yield self.__redis_model_graph.update_graph(username, title, timescale,
                keys, graph_type)

        request.setResponseCode(303)
        request.redirect('/')
        request.finish()

    @straighten_out_request
    def get_graph(self, request, graph_username, title):
        self._log.debug('get graph %s %s', graph_username, title)

        username = request.getCookie('username')

        # HACK: routes can't handle URLs with %2F in them ('/')
        # so replace '$2F' with '%2F' as we unquote the title
        title = urllib.unquote_plus(title.replace('$2F', '%2F'))

        graph_type = request.args.get('graph_type', '')
        timescale = request.args.get('timescale', '')
        force_max_value = float(request.args.get('max', 0))

        for each in [graph_type, timescale]:
            if each == '':
                request.setResponseCode(400)
                return ''

        self.__finish_get_graph(request, username, graph_username, title,
                graph_type, timescale, force_max_value)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_graph(self, request, username, graph_username, title,
            graph_type, timescale, force_max_value):

        graphs = yield self.__redis_model_graph.get_graphs(graph_username)

        graph_details = yield self.__get_graph_details(title, graphs[title],
                graph_type, timescale)

        template = self.__template_lookup.get_template('graph.mako')

        ret = template.render(username=username, graph_username=graph_username,
                title=title, graph_type=graph_type, graph=[graph_details],
                force_max_value=force_max_value).encode('utf8')

        request.write(ret)
        request.finish()

    # AJAX calls to manipulate user state
    @straighten_out_request
    def post_graph_ordering(self, request):
        new_ordering = request.args.get('new_ordering', '')
        username = request.getCookie('username')

        if new_ordering == '':
            request.setResponseCode(400)
            return ''

        new_ordering = simplejson.loads(new_ordering)

        self.__finish_post_graph_ordering(request, username, new_ordering)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_post_graph_ordering(self, request, username, new_ordering):
        yield self.__redis_model_graph.update_ordering(username, new_ordering)

        request.write('')
        request.finish()

    @straighten_out_request
    def post_add_graph_from_other_user(self, request):
        username = request.getCookie('username')

        graph_username = request.args.get('graph_username', '')
        title = request.args.get('title', '')
        timescale = request.args.get('timescale', None)
        graph_type = request.args.get('graph_type', None)

        if graph_username == '' or title == '':
            request.setResponseCode(400)
            return ''

        self.__finish_post_add_graph_from_other_user(request, username,
                graph_username, title, timescale, graph_type)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_post_add_graph_from_other_user(self, request, username,
            graph_username, title, timescale, graph_type):

        graphs = yield self.__redis_model_graph.get_graphs(graph_username)

        if title in graphs:
            if not timescale:
                timescale = graphs[title]['timescale']
            if not graph_type:
                graph_type = graphs[title]['graph_type']

            yield self.__redis_model_graph.update_graph(username, title,
                    timescale, graphs[title]['fields'], graph_type)

        request.setResponseCode(303)
        request.redirect('/')
        request.finish()

    # API for dealing with data
    @straighten_out_request
    def post_data(self, request, component):
        self._log.debug('posting data for %s %s', component, request.args)

        deferreds = []

        for metric, value in request.args.iteritems():
            deferred = self.__redis_model_data.update_metric(component, metric,
                    int(value))

            deferreds.append(deferred)

        defer_list = defer.DeferredList(deferreds, consumeErrors=True)
        defer_list.addCallback(self.__finish_post_data, request)

        return NOT_DONE_YET

    def __finish_post_data(self, responses, request):
        errors = []
        for (success, exception) in responses:
            if not success:
                errors.append(exception.value.message)

        if errors:
            request.setResponseCode(400)
            request.write(simplejson.dumps(errors))
        else:
            request.write('OK')

        request.finish()

    @straighten_out_request
    def get_data(self, request, component, metric):
        timescale = request.args.get('ts', '6h')

        if timescale not in self.timescales:
            timescale = '6h'

        self.__finish_get_data(request, component, metric, timescale)

        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_get_data(self, request, component, metric, timescale):
        data = yield self.__redis_model_data.get_data(component, metric,
                timescale)

        request.write(simplejson.dumps(data))
        request.finish()

    @straighten_out_request
    def delete_data(self, request, component, metric=None):
        self.__finish_delete_data(request, component, metric)
        return NOT_DONE_YET

    @defer.inlineCallbacks
    def __finish_delete_data(self, request, component, metric):
        yield self.__redis_model_data.delete_data(component, metric)
        request.write('OK')
        request.finish()

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

    # Helpers
    @defer.inlineCallbacks
    def __get_graph_details(self, title, graph, graph_type=None,
            timescale=None):

        if not graph_type or graph_type not in self.graph_types:
            graph_type = graph['graph_type']

        if not timescale or timescale not in self.timescales:
            timescale = graph['timescale']

        fields = graph['fields']
        fields.sort() # TODO: migrate graphs so fields are already sorted

        time_per_data_point = 60*1000

        if timescale == '36h':
            time_per_data_point = 5*60*1000
        elif timescale == '1w':
            time_per_data_point = 30*60*1000
        elif timescale == '1m':
            time_per_data_point = 2*60*60*1000
        elif timescale == '6m':
            time_per_data_point = 12*60*60*1000

        line_names = []
        data_rows = []

        for each_field in fields:
            component, metric = each_field.split('|')[:2]

            metrics = yield self.__redis_model_data.get_metrics(component)

            # Handle wildcard metrics
            matching_metrics = []
            if '*' in metric:
                metric_re = metric.replace('*', '[a-zA-Z0-9_\.:-]*')
            else:
                metric_re = metric

            metric_re = '^%s$' % metric_re

            for each_metric in metrics:
                if re.match(metric_re, each_metric):
                    matching_metrics.append(each_metric)

            if len(matching_metrics) == 0:
                line_name = '%s: %s - NO DATA' % (component, metric)
                line_names.append(line_name.encode('utf8'))

                data = yield self.__redis_model_data.get_data(component,
                        metric, timescale)

                data_rows.append(data)

            else:
                for each_metric in matching_metrics:
                    line_name = '%s: %s' % (component, each_metric)
                    line_names.append(line_name.encode('utf8'))

                    data = yield self.__redis_model_data.get_data(component,
                            each_metric, timescale)

                    data_rows.append(data)

        # Protoviz wants time in ms
        current_time_slot = (int(time.time()) / 60 * 60) * 1000

        if len(data_rows) > 0:
            length = max([len(row) for row in data_rows])

            if graph_type == 'stacked':
                max_value = max([sum(column) for column in zip(*data_rows)])
            else:
                max_value = max([max(row) for row in data_rows])
        else:
            length = 0
            max_value = 0

        # HACK: routes can't handle URLs with %2F in them ('/')
        # so replace '%2F' with '$2F' as we quote the title
        title_urlencoded = urllib.quote_plus(title).replace('%2F', '$2F')

        defer.returnValue((title, title_urlencoded, graph_type,
                urllib.quote_plus(graph_type), timescale,
                time_per_data_point, line_names, data_rows, current_time_slot,
                length, max_value))

def set_up_server(port, log_path, log_level):
    # Set up logging
    log = logging.getLogger('tinyfeedback')
    level = getattr(logging, log_level, logging.INFO)
    log.setLevel(level)

    if log_path != '':
        dir_path = os.path.dirname(log_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, 0755)

        handler = logging.handlers.RotatingFileHandler(log_path,
                maxBytes=100*1024*1024, backupCount=5)

    else:
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log.addHandler(handler)

    # Connect to redis
    redis_model_data = redis_model.Data('127.0.0.1')
    redis_model_data.connect()

    redis_model_graph = redis_model.Graph('127.0.0.1')
    redis_model_graph.connect()

    # Set up the webserver
    controller = Controller(redis_model_data, redis_model_graph, log)

    dispatcher = txroutes.Dispatcher()

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

    dispatcher.connect('get_graph', '/graph/{graph_username}/{title}',
            controller=controller, action='get_graph',
            conditions=dict(method=['GET']))

    # AJAX calls to manipulate user state
    dispatcher.connect('post_graph_ordering', '/graph_ordering',
            controller=controller, action='post_graph_ordering',
            conditions=dict(method=['POST']))

    dispatcher.connect('post_add_graph_from_other_user', '/add_graph',
            controller=controller, action='post_add_graph_from_other_user',
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
