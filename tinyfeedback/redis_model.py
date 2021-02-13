import re
import time

import redis
import simplejson
from twisted.internet import defer, protocol, reactor
import txredisapi


class Graph(object):
    '''
    tinyfeedback:usernames - all the usernames we know about
    tinyfeedback:graph:<username>:all_graphs - dictionary of graphs by title
    '''

    def __init__(self, host):
        self.__host = host

    @defer.inlineCallbacks
    def connect(self, poolsize=None):
        if not poolsize:
            poolsize = 50

        self.__redis = yield txredisapi.ConnectionPool(self.__host,
                poolsize=poolsize)

    @defer.inlineCallbacks
    def add_username(self, username):
        key = 'tinyfeedback:usernames'
        yield self.__redis.sadd(key, username)

    @defer.inlineCallbacks
    def remove_username(self, username):
        key = 'tinyfeedback:usernames'
        yield self.__redis.srem(key, username)

    @defer.inlineCallbacks
    def get_graphs_per_user(self):
        user_key = 'tinyfeedback:usernames'
        usernames = yield self.__redis.smembers(user_key)

        graphs_per_user = []

        if usernames is None or len(usernames) == 0:
            defer.returnValue(graphs_per_user)

        keys = ['tinyfeedback:graph:%s:all_graphs' % each_username for \
                each_username in usernames]

        user_graphs = yield self.__redis.mget(keys)

        for i, each_username in enumerate(usernames):
            if not user_graphs[i]:
                num_graphs = 0
            else:
                num_graphs = len(simplejson.loads(user_graphs[i]))

            graphs_per_user.append((each_username, num_graphs))

        # Sort usernames by the number of graphs they have
        graphs_per_user.sort(cmp=lambda x, y: y[1] - x[1])

        defer.returnValue(graphs_per_user)

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
    def update_graph(self, username, title, timescale, fields, graph_type,
            updates_infrequently):

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
                graphs[title]['updates_infrequently'] = updates_infrequently

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


class BlockingData(object):
    def __init__(self, host):
        self.__redis = redis.StrictRedis(host=host)

    def __get_max_min(self, subset):
        min_value = min(subset)
        max_value = max(subset)

        if subset.index(min_value) < subset.index(max_value):
            return min_value, max_value
        else:
            return max_value, min_value

    def __return_up_to_date_data(self, pipeline, component, metric, update_value=None):
        keys = ['tinyfeedback:data:component:%s:metric:%s:last_updated' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        data = pipeline.mget(keys)
        data_changed = False

        # Load the data in the format we want
        if data[0] is None:
            last_updated = int(time.time()) / 60 * 60
        else:
            last_updated = int(data[0])

        if data[1] is None:
            info_6h = [0] * 360 # 1 min each
        else:
            info_6h = simplejson.loads(data[1])

            # HACK: backwards compatability
            if isinstance(info_6h, dict):
                last_updated = info_6h['last_updated']
                info_6h = info_6h['data']
                data_changed = True

        if data[2] is None:
            info_36h = [0] * 432 # 5 min each
        else:
            info_36h = simplejson.loads(data[2])

            # HACK: backwards compatability
            if isinstance(info_36h, dict):
                info_36h = info_36h['data']
                data_changed = True

        if data[3] is None:
            info_1w = [0] * 336 # 30 min each
        else:
            info_1w = simplejson.loads(data[3])

            # HACK: backwards compatability
            if isinstance(info_1w, dict):
                info_1w = info_1w['data']
                data_changed = True

        if data[4] is None:
            info_1m = [0] * 360 # 2 hours each
        else:
            info_1m = simplejson.loads(data[4])

            # HACK: backwards compatability
            if isinstance(info_1m, dict):
                info_1m = info_1m['data']
                data_changed = True

        if data[5] is None:
            info_6m = [0] * 360 # 12 hours each
        else:
            info_6m = simplejson.loads(data[5])

            # HACK: backwards compatability
            if isinstance(info_6m, dict):
                info_6m = info_6m['data']
                data_changed = True

        update_to = int(time.time()) / 60 * 60

        while last_updated < update_to:
            data_changed = True
            last_updated += 60

            # First, save the roll up values
            if last_updated % 600 == 0:
                first, second = self.__get_max_min(info_6h[-10:])
                info_36h[-2] = first
                info_36h[-1] = second

            if last_updated % 3600 == 0:
                first, second = self.__get_max_min(info_36h[-12:])
                info_1w[-2] = first
                info_1w[-1] = second

            if last_updated % 14400 == 0:
                first, second = self.__get_max_min(info_1w[-8:])
                info_1m[-2] = first
                info_1m[-1] = second

            if last_updated % 86400 == 0:
                first, second = self.__get_max_min(info_1m[-12:])
                info_6m[-2] = first
                info_6m[-1] = second

            # Then, extend arrays
            info_6h.append(None)

            if last_updated % 600 == 0:
                info_36h.extend([0, 0])

            if last_updated % 3600 == 0:
                info_1w.extend([0, 0])

            if last_updated % 14400 == 0:
                info_1m.extend([0, 0])

            if last_updated % 86400 == 0:
                info_6m.extend([0, 0])

        if update_value is not None or data_changed:
            if update_value is not None:
                info_6h[-1] = update_value
                data_changed = True

            # Do partial roll ups
            for (block_size, unit_size, small_array, large_array) in (
                    (600, 60, info_6h, info_36h),
                    (3600, 300, info_36h, info_1w),
                    (14400, 1800, info_1w, info_1m),
                    (86400, 7200, info_1m, info_6m),
                    ):

                partial_update_range = (last_updated % block_size /
                        unit_size) + 1

                first, second = self.__get_max_min(
                        small_array[-1*partial_update_range:])

                large_array[-2] = first
                large_array[-1] = second

        return (data_changed, last_updated, info_6h[-360:], info_36h[-432:],
                info_1w[-336:], info_1m[-360:], info_6m[-360:])

    def update_metric(self, component, metric, value):
        # Make sure values are sane
        if not re.match('^[A-Za-z0-9_\.:-]+$', component):
            return
            # XXX should return this error to the end-user
            raise ValueError('Bad component: %s (must only contain A-Z, a-z, 0-9, _, -, :, and .)' % component)

        if not re.match('^[A-Za-z0-9_\.:-]+$', metric):
            return
            # XXX should return this error to the end-user
            raise ValueError('Bad metric: %s (must only contain A-Z, a-z, 0-9, _, -, :, and .)' % metric)

        component = component[:128]
        metric = metric[:128]
        value = int(value)

        # Now we can actually update
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                'tinyfeedback:data:component:%s:metric:%s:last_updated' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        with self.__redis.pipeline() as pipeline:
            while True:
                try:
                    pipeline.watch(keys)

                    data = pipeline.mget(keys[:2])

                    # Load the data
                    _, last_updated, info_6h, info_36h, info_1w, info_1m, \
                            info_6m = self.__return_up_to_date_data(pipeline,
                                component, metric, value)

                    pipeline.multi()

                    # Make sure the component is listed
                    if data[0] is None:
                        components = [component]
                        pipeline.set(keys[0], simplejson.dumps(components))

                    else:
                        components = simplejson.loads(data[0])
                        if component not in components:
                            components.append(component)
                            components.sort()
                            pipeline.set(keys[0], simplejson.dumps(components))

                    # Make sure the metric is listed
                    if data[1] is None:
                        metrics = [metric]
                        pipeline.set(keys[1], simplejson.dumps(metrics))

                    else:
                        metrics = simplejson.loads(data[1])
                        if metric not in metrics:
                            metrics.append(metric)
                            metrics.sort()
                            pipeline.set(keys[1], simplejson.dumps(metrics))

                    # Store the values
                    pipeline.set(keys[2], last_updated)
                    pipeline.set(keys[3], simplejson.dumps(info_6h))
                    pipeline.set(keys[4], simplejson.dumps(info_36h))
                    pipeline.set(keys[5], simplejson.dumps(info_1w))
                    pipeline.set(keys[6], simplejson.dumps(info_1m))
                    pipeline.set(keys[7], simplejson.dumps(info_6m))

                    pipeline.execute()
                    break

                except redis.WatchError:
                    continue

class Data(object):
    '''
    tinyfeedback:data:list_components - all components
    tinyfeedback:data:component:<component>:list_metrics - all metrics for a component
    tinyfeedback:data:component:<component>:metric:<metric>:last_updated - last update to metric
    tinyfeedback:data:component:<component>:metric:<metric>:<timescale> - data
    '''
    def __init__(self, host):
        self.__host = host
        self.__update_metric_limit = defer.DeferredSemaphore(25)

    def __get_max_min(self, subset):
        min_value = min(subset)
        max_value = max(subset)

        if subset.index(min_value) < subset.index(max_value):
            return min_value, max_value
        else:
            return max_value, min_value

    @defer.inlineCallbacks
    def connect(self, poolsize=None):
        if not poolsize:
            poolsize = 200

        self.__redis = yield txredisapi.ConnectionPool(self.__host,
                poolsize=poolsize)

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
                    metric_keys = ['tinyfeedback:data:component:%s:metric:%s:last_updated' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:6h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:36h' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1w' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:1m' % (component, each_metric),
                            'tinyfeedback:data:component:%s:metric:%s:6m' % (component, each_metric),
                            ]

                    last_updated = yield self.__redis.get(metric_keys[0])

                    if not last_updated:
                        continue

                    if current_time_slot - last_updated > (7 * 24 * 60 * 60):
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
    def get_data(self, component, metric, timescale, updates_infrequently=False):
        keys = ['tinyfeedback:data:list_components',
                'tinyfeedback:data:component:%s:list_metrics' % component,
                'tinyfeedback:data:component:%s:metric:%s:last_updated' % (component, metric),
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

                # If the metric does not exist, just return 0's
                metrics = yield self.__redis.get(keys[1])

                if metrics is not None:
                    metrics = simplejson.loads(metrics)

                if metrics is None or metric not in metrics:
                    if timescale in ['6h', '1m', '6m']:
                        yield transaction.discard()
                        defer.returnValue([0] * 360)
                    elif timescale == '36h':
                        yield transaction.discard()
                        defer.returnValue([0] * 432)
                    elif timescale == '1w':
                        yield transaction.discard()
                        defer.returnValue([0] * 336)

                # Try to get the data
                data_changed, last_updated, info_6h, info_36h, info_1w, \
                        info_1m, info_6m = yield self.__return_up_to_date_data(
                            component, metric)

                if data_changed:
                    yield transaction.mset({keys[2]: last_updated,
                            keys[3]: simplejson.dumps(info_6h),
                            keys[4]: simplejson.dumps(info_36h),
                            keys[5]: simplejson.dumps(info_1w),
                            keys[6]: simplejson.dumps(info_1m),
                            keys[7]: simplejson.dumps(info_6m),
                            })

                    yield transaction.commit()

                else:
                    yield transaction.discard()

                break

            except txredisapi.WatchError:
                continue

        if timescale == '6h':
            data = info_6h
        elif timescale == '36h':
            data = info_36h
        elif timescale == '1w':
            data = info_1w
        elif timescale == '1m':
            data = info_1m
        elif timescale == '6m':
            data = info_6m

        last_seen_value = 0
        for i in xrange(len(data)):
            if data[i] is None:
                data[i] = last_seen_value

            if updates_infrequently and data[i] is not None:
                last_seen_value = data[i]

        defer.returnValue(data)

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
                            'tinyfeedback:data:component:%s:metric:%s:last_updated' % (component, each_metric),
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
    def __return_up_to_date_data(self, component, metric, update_value=None):
        keys = ['tinyfeedback:data:component:%s:metric:%s:last_updated' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:36h' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1w' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:1m' % (component, metric),
                'tinyfeedback:data:component:%s:metric:%s:6m' % (component, metric),
                ]

        data = yield self.__redis.mget(keys)
        data_changed = False

        # Load the data in the format we want
        if data[0] is None:
            last_updated = int(time.time()) / 60 * 60
        else:
            last_updated = data[0]

        if data[1] is None:
            info_6h = [0] * 360 # 1 min each
        else:
            info_6h = simplejson.loads(data[1])

            # HACK: backwards compatability
            if isinstance(info_6h, dict):
                last_updated = info_6h['last_updated']
                info_6h = info_6h['data']
                data_changed = True

        if data[2] is None:
            info_36h = [0] * 432 # 5 min each
        else:
            info_36h = simplejson.loads(data[2])

            # HACK: backwards compatability
            if isinstance(info_36h, dict):
                info_36h = info_36h['data']
                data_changed = True

        if data[3] is None:
            info_1w = [0] * 336 # 30 min each
        else:
            info_1w = simplejson.loads(data[3])

            # HACK: backwards compatability
            if isinstance(info_1w, dict):
                info_1w = info_1w['data']
                data_changed = True

        if data[4] is None:
            info_1m = [0] * 360 # 2 hours each
        else:
            info_1m = simplejson.loads(data[4])

            # HACK: backwards compatability
            if isinstance(info_1m, dict):
                info_1m = info_1m['data']
                data_changed = True

        if data[5] is None:
            info_6m = [0] * 360 # 12 hours each
        else:
            info_6m = simplejson.loads(data[5])

            # HACK: backwards compatability
            if isinstance(info_6m, dict):
                info_6m = info_6m['data']
                data_changed = True

        update_to = int(time.time()) / 60 * 60

        while last_updated < update_to:
            data_changed = True
            last_updated += 60

            # First, save the roll up values
            if last_updated % 600 == 0:
                first, second = self.__get_max_min(info_6h[-10:])
                info_36h[-2] = first
                info_36h[-1] = second

            if last_updated % 3600 == 0:
                first, second = self.__get_max_min(info_36h[-12:])
                info_1w[-2] = first
                info_1w[-1] = second

            if last_updated % 14400 == 0:
                first, second = self.__get_max_min(info_1w[-8:])
                info_1m[-2] = first
                info_1m[-1] = second

            if last_updated % 86400 == 0:
                first, second = self.__get_max_min(info_1m[-12:])
                info_6m[-2] = first
                info_6m[-1] = second

            # Then, extend arrays
            info_6h.append(None)

            if last_updated % 600 == 0:
                info_36h.extend([0, 0])

            if last_updated % 3600 == 0:
                info_1w.extend([0, 0])

            if last_updated % 14400 == 0:
                info_1m.extend([0, 0])

            if last_updated % 86400 == 0:
                info_6m.extend([0, 0])

        if update_value is not None or data_changed:
            if update_value is not None:
                info_6h[-1] = update_value
                data_changed = True

            # Do partial roll ups
            for (block_size, unit_size, small_array, large_array) in (
                    (600, 60, info_6h, info_36h),
                    (3600, 300, info_36h, info_1w),
                    (14400, 1800, info_1w, info_1m),
                    (86400, 7200, info_1m, info_6m),
                    ):

                partial_update_range = (last_updated % block_size /
                        unit_size) + 1

                first, second = self.__get_max_min(
                        small_array[-1*partial_update_range:])

                large_array[-2] = first
                large_array[-1] = second

        defer.returnValue((data_changed, last_updated, info_6h[-360:],
                info_36h[-432:], info_1w[-336:], info_1m[-360:], info_6m[-360:]))
