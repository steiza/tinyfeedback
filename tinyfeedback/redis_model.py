import re
import time

import simplejson
from twisted.internet import defer, protocol, reactor
import txredisapi


class Graph(object):
    '''
    tinyfeedback:graph:<username>:all_graphs - dictionary of graphs by title
    '''

    def __init__(self, host):
        self.__host = host

    @defer.inlineCallbacks
    def connect(self):
        self.__redis = yield txredisapi.ConnectionPool(self.__host, poolsize=50)

    @defer.inlineCallbacks
    def get_graphs(self, username):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        graphs = yield self.__redis.get(key)

        if not graphs:
            defer.returnValue({})

        else:
            defer.returnValue(simplejson.loads(graphs))

    @defer.inlineCallbacks
    def remove_graph(self, username, title):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        while True:
            try:
                transaction = yield self.__redis.multi(key)

                graphs = yield self.__redis.get(key)

                if graphs:
                    graphs = simplejson.loads(graphs)

                if not graphs or title not in graphs:
                    yield transaction.discard()
                    break

                removed_ordering = graphs[title]['ordering']

                del graphs[title]

                # Reorder the remaining graphs
                for each in graphs.itervalues():
                    if each['ordering'] > removed_ordering:
                        each['ordering'] -= 1

                yield transaction.set(key, simplejson.dumps(graphs))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def update_graph(self, username, title, timescale, fields, graph_type):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        fields.sort()

        while True:
            try:
                transaction = yield self.__redis.multi(key)

                graphs = yield self.__redis.get(key)

                if not graphs:
                    graphs = {}
                else:
                    graphs = simplejson.loads(graphs)

                if title not in graphs:
                    # Find the next ordering
                    if len(graphs) == 0:
                        max_ordering = 0
                    elif len(graphs) == 1:
                        max_ordering = graphs.values()[0]['ordering'] + 1
                    else:
                        max_ordering = max( [each['ordering'] for each in \
                                graphs.itervalues()] ) + 1

                    graphs[title] = {'ordering': max_ordering}

                graphs[title]['timescale'] = timescale
                graphs[title]['fields'] = fields
                graphs[title]['graph_type'] = graph_type

                yield transaction.set(key, simplejson.dumps(graphs))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def update_ordering(self, username, new_ordering):
        key = 'tinyfeedback:graph:%s:all_graphs' % username

        while True:
            try:
                transaction = yield self.__redis.multi(key)

                graphs = yield self.__redis.get(key)

                if not graphs:
                    graphs = {}
                else:
                    graphs = simplejson.loads(graphs)

                for index, title in enumerate(new_ordering):
                    if title in graphs:
                        graphs[title]['ordering'] = index

                yield transaction.set(key, simplejson.dumps(graphs))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue


class Data(object):
    '''
    tinyfeedback:data:list_components - all components
    tinyfeedback:data:component:<component>:list_metrics - all metrics for a component
    tinyfeedback:data:component:<component>:metric:<metric>:<timescale> - data
    '''

    def __init__(self, host):
        self.__host = host
        self.__update_metric_limit = defer.DeferredSemaphore(25)

    @defer.inlineCallbacks
    def connect(self):
        self.__redis = yield txredisapi.ConnectionPool(self.__host, poolsize=200)

    @defer.inlineCallbacks
    def get_components(self):
        components = yield self.__redis.get('tinyfeedback:data:list_components')

        if not components:
            defer.returnValue([])
        else:
            defer.returnValue(simplejson.loads(components))

    @defer.inlineCallbacks
    def delete_metrics_older_than_a_week(self, component):
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                ]

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                components, metrics = yield self.__redis.mget(keys)

                if not components:
                    components = []
                else:
                    components = simplejson.loads(components)

                if not metrics:
                    metrics = []
                else:
                    metrics = simplejson.loads(metrics)

                if component not in components or len(metrics) == 0:
                    yield transaction.discard()
                    break

                current_time_slot = int(time.time()) / 60 * 60
                metric_changed = False

                for each_metric in metrics:
                    metric_keys = ['tinyfeedback:data:component:%s:metric:%s:6h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:36h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1w' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1m' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:6m' % (component, each_metric),
                            ]

                    info_6h = yield self.__redis.get(metric_keys[0])

                    if not info_6h:
                        continue

                    info_6h = simplejson.loads(info_6h)

                    if current_time_slot - info_6h['last_updated'] > \
                            (7 * 24 * 60 * 60):

                        metric_changed = True
                        metrics.remove(each_metric)

                        for each_key in metric_keys:
                            yield transaction.delete(each_key)

                if metric_changed:
                    yield transaction.set(keys[1], simplejson.dumps(metrics))

                    if len(metrics) == 0:
                        components.remove(component)
                        yield transaction.set(keys[0], simplejson.dumps(components))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def get_metrics(self, component):
        key = 'tinyfeedback:data:component:%s:list_metrics' % component
        metrics = yield self.__redis.get(key)

        if not metrics:
            defer.returnValue([])
        else:
            defer.returnValue(simplejson.loads(metrics))

    @defer.inlineCallbacks
    def get_data(self, component, metric, timescale):
        key = 'tinyfeedback:data:component:%s:metric:%s:%s' % (component, metric, timescale)

        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        data = None

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                info_6h = yield self.__redis.get(keys[2])

                if not info_6h:
                    if timescale in ['6h', '1m', '6m']:
                        yield transaction.discard()
                        defer.returnValue([0] * 360)
                    elif timescale == '36h':
                        yield transaction.discard()
                        defer.returnValue([0] * 432)
                    elif timescale == '1w':
                        yield transaction.discard()
                        defer.returnValue([0] * 336)
                else:
                    info_6h = simplejson.loads(info_6h)

                current_time_slot = int(time.time()) / 60 * 60
                time_since_update = current_time_slot - info_6h['last_updated']

                # If we haven't updated in over 10 minutes, do a long roll up
                if time_since_update / 60 > 10:
                    yield self.__do_long_roll_up(keys, transaction, time_since_update,
                            info_6h)

                    info_6h['last_updated'] = current_time_slot
                    yield transaction.set(keys[2], simplejson.dumps(info_6h))

                # Otherwise do the normal roll up
                elif time_since_update > 0:
                    while current_time_slot > info_6h['last_updated']:
                        info_6h['updates_since_last_roll_up'] += 1
                        info_6h['last_updated'] += 60
                        info_6h['data'].append(0)

                        if info_6h['updates_since_last_roll_up'] >= 10:
                            yield self.__do_roll_up(keys, transaction, info_6h)

                            info_6h['updates_since_last_roll_up'] -= 10

                    # Truncate data to the most recent values
                    info_6h['data'] = info_6h['data'][-360:]

                    info_6h['last_updated'] = current_time_slot
                    yield transaction.set(keys[2], simplejson.dumps(info_6h))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

        data = yield self.__redis.get(key)

        if not data:
            if timescale in ['6h', '1m', '6m']:
                defer.returnValue([0] * 360)
            elif timescale == '36h':
                defer.returnValue([0] * 432)
            elif timescale == '1w':
                defer.returnValue([0] * 336)
        else:
            data = simplejson.loads(data)
            defer.returnValue(data['data'])

    @defer.inlineCallbacks
    def delete_data(self, component, metric=None):
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                ]

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                components, metrics = yield self.__redis.mget(keys)

                if not components:
                    components = []
                else:
                    components = simplejson.loads(components)

                if not metrics:
                    metrics = []
                else:
                    metrics = simplejson.loads(metrics)

                # If the requested object does not exist, we are done
                if component not in components or \
                        (metric and metric not in metrics):

                    yield transaction.discard()
                    break

                # If the metric is not specified, grab all metrics
                if not metric:
                    metrics_to_delete = metrics
                else:
                    metrics_to_delete = [metric]

                # Delete the data
                for each_metric in metrics_to_delete:
                    metric_keys = [
                            'tinyfeedback:data:component:%s:metric:%s:6h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:36h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1w' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1m' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:6m' % (component, each_metric),
                            ]

                    for each_key in metric_keys:
                        yield transaction.delete(each_key)

                # If a metric was specified, just remove it
                if metric:
                    metrics.remove(each_metric)
                    yield transaction.set(keys[1], simplejson.dumps(metrics))

                    if len(metrics) == 0:
                        components.remove(component)
                        yield transaction.set(keys[0], simplejson.dumps(components))

                # Otherwise delete the component
                else:
                    components.remove(component)
                    yield transaction.set(keys[0], simplejson.dumps(components))
                    yield transaction.delete(keys[1])

                yield transaction.commit()

                break

            except txredisapi.WatchError:
                continue

    @defer.inlineCallbacks
    def update_metric(self, component, metric, value):
        # Make sure values are sane
        if not re.match('^[A-Za-z0-9_\.:-]+$', component):
            raise ValueError('Bad component: %s (must only contain A-Z, a-z, 0-9, _, -, :, and .)' % component)

        if not re.match('^[A-Za-z0-9_\.:-]+$', metric):
            raise ValueError('Bad metric: %s (must only contain A-Z, a-z, 0-9, _, -, :, and .)' % metric)

        yield self.__update_metric_limit.acquire()

        component = component[:128]
        metric = metric[:128]
        value = int(value)

        # Now we can actually update
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        while True:
            try:
                transaction = yield self.__redis.multi(keys)

                components, metrics = yield self.__redis.mget(keys[:2])
                info_6h = yield self.__redis.get(keys[2])

                # Make sure component is listed
                if not components:
                    components = [component]
                    yield transaction.set(keys[0], simplejson.dumps(components))

                else:
                    components = simplejson.loads(components)
                    if component not in components:
                        components.append(component)
                        components.sort()
                        yield transaction.set(keys[0],
                                simplejson.dumps(components))

                # Make sure metric is listed
                if not metrics:
                    metrics = [metric]
                    yield transaction.set(keys[1], simplejson.dumps(metrics))

                else:
                    metrics = simplejson.loads(metrics)
                    if metric not in metrics:
                        metrics.append(metric)
                        metrics.sort()
                        yield transaction.set(keys[1],
                                simplejson.dumps(metrics))

                # Now we're actually ready to deal with the data
                current_time_slot = int(time.time()) / 60 * 60

                if not info_6h:
                    info_6h = {'data': [0] * 360, # Every 1 min
                            'updates_since_last_roll_up': 0,
                            'last_updated': current_time_slot,
                            }

                else:
                    info_6h = simplejson.loads(info_6h)

                time_since_update = current_time_slot - info_6h['last_updated']

                # If we haven't updated in over 10 minutes, do a long roll up
                if time_since_update / 60 > 10:
                    yield self.__do_long_roll_up(keys, transaction,
                            time_since_update, info_6h)

                # Otherwise do the normal roll up
                else:
                    while current_time_slot > info_6h['last_updated']:
                        info_6h['updates_since_last_roll_up'] += 1
                        info_6h['last_updated'] += 60
                        info_6h['data'].append(0)

                        if info_6h['updates_since_last_roll_up'] >= 10:
                            # Make sure the value is set before roll up
                            if current_time_slot == info_6h['last_updated']:
                                info_6h['data'][-1] = value

                            yield self.__do_roll_up(keys, transaction, info_6h)

                            info_6h['updates_since_last_roll_up'] -= 10

                    # Truncate data to the most recent values
                    info_6h['data'] = info_6h['data'][-360:]

                # At last, update the value
                info_6h['data'][-1] = value
                info_6h['last_updated'] = current_time_slot

                yield transaction.set(keys[2], simplejson.dumps(info_6h))

                yield transaction.commit()
                break

            except txredisapi.WatchError:
                continue

        yield self.__update_metric_limit.release()

    @defer.inlineCallbacks
    def __load_long_data(self, keys, transaction):
        info_36h, info_1w, info_1m, info_6m = yield self.__redis.mget(keys[3:])

        # Makes sure the data is loaded
        if not info_36h:
            info_36h = {'data': [0] * 432, # Every 5 min
                    'updates_since_last_roll_up': 0,
                    }

            yield transaction.set(keys[3], simplejson.dumps(info_36h))
        else:
            info_36h = simplejson.loads(info_36h)

        if not info_1w:
            info_1w = {'data': [0] * 336, # Every 30 min
                    'updates_since_last_roll_up': 0,
                    }

            yield transaction.set(keys[4], simplejson.dumps(info_1w))
        else:
            info_1w = simplejson.loads(info_1w)

        if not info_1m:
            info_1m = {'data': [0] * 360, # Every 2 hours
                    'updates_since_last_roll_up': 0,
                    }

            yield transaction.set(keys[5], simplejson.dumps(info_1m))
        else:
            info_1m = simplejson.loads(info_1m)

        if not info_6m:
            info_6m = {'data': [0] * 360, # Every 12 hours
                    }

            yield transaction.set(keys[6], simplejson.dumps(info_6m))
        else:
            info_6m = simplejson.loads(info_6m)

        defer.returnValue((info_36h, info_1w, info_1m, info_6m))

    @defer.inlineCallbacks
    def __do_roll_up(self, keys, transaction, info_6h):
        info_36h, info_1w, info_1m, info_6m = yield self.__load_long_data(
                keys, transaction)

        # Roll up for 36h
        subset = info_6h['data'][-10:]
        min_value = min(subset)
        max_value = max(subset)

        if subset.index(min_value) < subset.index(max_value):
            info_36h['data'].extend([min_value, max_value])
        else:
            info_36h['data'].extend([max_value, min_value])

        info_36h['updates_since_last_roll_up'] += 2
        info_36h['data'] = info_36h['data'][2:]

        # Roll up for 1w
        if info_36h['updates_since_last_roll_up'] >= 12:
            info_36h['updates_since_last_roll_up'] -= 12

            subset = info_36h['data'][-12:]
            min_value = min(subset)
            max_value = max(subset)

            if subset.index(min_value) < subset.index(max_value):
                info_1w['data'].extend([min_value, max_value])
            else:
                info_1w['data'].extend([max_value, min_value])

            info_1w['updates_since_last_roll_up'] += 2
            info_1w['data'] = info_1w['data'][2:]

        # Roll up for 1m
        if info_1w['updates_since_last_roll_up'] >= 8:
            info_1w['updates_since_last_roll_up'] -= 8

            subset = info_1w['data'][-8:]
            min_value = min(subset)
            max_value = max(subset)

            if subset.index(min_value) < subset.index(max_value):
                info_1m['data'].extend([min_value, max_value])
            else:
                info_1m['data'].extend([max_value, min_value])

            info_1m['updates_since_last_roll_up'] += 2
            info_1m['data'] = info_1m['data'][2:]

        # Roll up for 6m
        if info_1m['updates_since_last_roll_up'] >= 12:
            info_1m['updates_since_last_roll_up'] -= 12

            subset = info_1m['data'][-12:]
            min_value = min(subset)
            max_value = max(subset)

            if subset.index(min_value) < subset.index(max_value):
                info_6m['data'].extend([min_value, max_value])
            else:
                info_6m['data'].extend([max_value, min_value])

            info_6m['data'] = info_6m['data'][2:]

        yield transaction.set(keys[3], simplejson.dumps(info_36h))
        yield transaction.set(keys[4], simplejson.dumps(info_1w))
        yield transaction.set(keys[5], simplejson.dumps(info_1m))
        yield transaction.set(keys[6], simplejson.dumps(info_6m))

    @defer.inlineCallbacks
    def __do_long_roll_up(self, keys, transaction, time_since_update, info_6h):
        info_36h, info_1w, info_1m, info_6m = yield self.__load_long_data(
                keys, transaction)

        # Roll up for 6h
        needed_updates = time_since_update / 60
        needed_updates_floor = min(needed_updates, 360)
        info_6h['data'].extend([0] * needed_updates_floor)
        info_6h['data'] = info_6h['data'][-360:]
        info_6h['updates_since_last_roll_up'] += needed_updates

        needed_updates = info_6h['updates_since_last_roll_up'] / 10
        info_6h['updates_since_last_roll_up'] %= 10

        yield transaction.set(keys[2], simplejson.dumps(info_6h))

        # Roll up for 36h
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 432 / 2)
            info_36h['data'].extend([0] * 2 * needed_updates_floor)
            info_36h['data'] = info_36h['data'][-432:]
            info_36h['updates_since_last_roll_up'] += needed_updates

            needed_updates = info_36h['updates_since_last_roll_up'] / 12
            info_36h['updates_since_last_roll_up'] %= 12

            yield transaction.set(keys[3], simplejson.dumps(info_36h))

        # Roll up for 1w
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 336 / 2)
            info_1w['data'].extend([0] * 2 * needed_updates_floor)
            info_1w['data'] = info_1w['data'][-336:]
            info_1w['updates_since_last_roll_up'] += needed_updates

            needed_updates = info_1w['updates_since_last_roll_up'] / 8
            info_1w['updates_since_last_roll_up'] %= 8

            yield transaction.set(keys[4], simplejson.dumps(info_1w))

        # Roll up for 1m
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 360 / 2)
            info_1m['data'].extend([0] * 2 * needed_updates_floor)
            info_1m['data'] = info_1m['data'][-360:]
            info_1m['updates_since_last_roll_up'] += needed_updates

            needed_updates = info_1m['updates_since_last_roll_up'] / 12
            info_1m['updates_since_last_roll_up'] %= 12

            yield transaction.set(keys[5], simplejson.dumps(info_1m))

        # Roll up for 6m
        if needed_updates > 0:
            needed_updates_floor = min(needed_updates, 360 / 2)
            info_6m['data'].extend([0] * 2 * needed_updates_floor)
            info_6m['data'] = info_6m['data'][-360:]

            yield transaction.set(keys[6], simplejson.dumps(info_6m))
