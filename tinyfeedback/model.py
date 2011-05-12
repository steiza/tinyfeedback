import datetime
import time
import urllib

import simplejson
from sqlalchemy import create_engine, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import asc, desc


DatabaseObject = declarative_base()

def bind_engine(engine):
    DatabaseObject.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=True)

# Helper methods for User
def ensure_user_exists(SessionMaker, username):
    session = SessionMaker()

    user_row = session.query(User).filter(User.username == username).all()

    if len(user_row) == 0:
        user = User(username)
        session.add(user)
        session.commit()
    else:
        user = user_row[0]

    user_id = user.id

    session.close()
    return user_id

# Helper methods for CustomGraph
def get_data_for_graph(SessionMaker, graph_id, title, graph_type, fields,
        timescale):

    session = SessionMaker()

    title_urlencoded = urllib.quote_plus(title)
    graph_type_urlencoded = urllib.quote_plus(graph_type)

    fields_dict = {}
    true = map(lambda _: 'true', fields)
    fields_dict.update(zip(fields, true))
    fields_urlencoded = urllib.urlencode(fields_dict)

    line_names = []
    data = []
    current_time = 0
    length = 0
    max_value = 0
    max_value_stacked = 0

    # sort the fields
    fields.sort()

    for each_field in fields:
        component, metric = each_field.split('|')[:2]

        # TODO: this looks like it should be distinct.
        data_rows = session.query(Data).filter(Data.component == component \
                ).filter(Data.metric == metric).all()

        line_names.append(str('%s: %s' % (component, metric)))

        if data_rows:
            data_array, should_save = data_rows[0].get_data(timescale)

            if should_save:
                session.merge(data_rows[0])

            length = max(length, len(data_array))
            max_value = max(max_value, max(data_array))
            max_value_stacked += max(data_array)

            data.append(data_array)
            current_time = int(time.mktime(
                    data_rows[0].last_updated.timetuple()))*1000

        else:
            data.append([])

    session.commit()

    time_per_data_point = 60*1000

    if timescale == '36h':
        time_per_data_point = 5*60*1000
    if timescale == '1w':
        time_per_data_point = 30*60*1000
    if timescale == '1m':
        time_per_data_point = 2*60*60*1000
    if timescale == '6m':
        time_per_data_point = 12*60*60*1000

    if graph_type == 'stacked':
        max_value = max_value_stacked

    return (graph_id, title, title_urlencoded, graph_type,
            graph_type_urlencoded, timescale, time_per_data_point,
            fields_urlencoded, line_names, data, current_time, length,
            max_value)

def get_graphs(SessionMaker, user_id):
    session = SessionMaker()

    graphs = []

    graph_rows = session.query(CustomGraph).filter(CustomGraph.user_id == \
            user_id).order_by(asc(CustomGraph.ordering)).all()

    session.close()

    for each_row in graph_rows:
        graph_name = each_row.title
        graph_type = each_row.graph_type or 'line'
        timescale = each_row.timescale
        graph_id = each_row.id

        fields = simplejson.loads(each_row.fields)

        graphs.append(get_data_for_graph(SessionMaker, graph_id, graph_name,
                graph_type, fields, timescale))

    return graphs

def update_ordering(SessionMaker, user_id, new_ordering):
    session = SessionMaker()

    for index, graph_id in enumerate(new_ordering):
        graph = session.query(CustomGraph).filter(CustomGraph.user_id == user_id
                ).filter(CustomGraph.id == int(graph_id)).one()

        graph.ordering = index

        session.merge(graph)

    session.commit()

def update_graph(SessionMaker, title, user_id, timescale, fields, graph_type):
    session = SessionMaker()

    try:
        graph = session.query(CustomGraph).filter(CustomGraph.title == title \
                ).filter(CustomGraph.user_id == user_id).one()

        graph.fields = simplejson.dumps(fields)
        graph.timescale = timescale
        graph.graph_type = graph_type
        session.add(graph)

    except NoResultFound:
        # Graph doesn't exist, add it
        ordering_rows = session.query(CustomGraph).filter(CustomGraph.user_id \
                == user_id).order_by(desc(CustomGraph.ordering)).all()

        if len(ordering_rows) == 0:
            ordering = 1
        else:
            ordering = ordering_rows[0].ordering + 1

        graph = CustomGraph(title, user_id, timescale, simplejson.dumps(fields),
                ordering, graph_type)

        session.add(graph)

    session.commit()

def remove_graph(SessionMaker, user_id, title):
    session = SessionMaker()

    try:
        graph = session.query(CustomGraph).filter(CustomGraph.user_id == \
                user_id).filter(CustomGraph.title == title).one()

        ordering = graph.ordering
        session.delete(graph)

        rows = session.query(CustomGraph).filter(CustomGraph.user_id == \
                user_id).filter(CustomGraph.ordering > ordering).all()

        for each in rows:
            each.ordering = each.ordering - 1
            session.add(each)

    except NoResultFound:
        # Graph doesn't exist
        return

    session.commit()

# Helper methods for Data
def get_data_sources(SessionMaker):
    data_sources = {}

    session = SessionMaker()
    rows = session.query(Data).all()

    for each in rows:
        if each.component not in data_sources:
            data_sources[each.component] = []

        data_sources[each.component].append(each.metric)

    session.close()

    return data_sources

def clean_out_metrics_older_than_a_week(SessionMaker, component):
    session = SessionMaker()

    rows = session.query(Data).filter(Data.component == component).filter(
            Data.data_6h == str([0] * 360)).filter(Data.data_36h == str(
                [0] * 432)).filter(Data.data_1w == str([0] * 336)).all()

    for each in rows:
        session.delete(each)

    session.commit()

# SQLAlchemy objects
class User(DatabaseObject):

    __tablename__ = 'user'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id       = Column('id', Integer, primary_key=True)
    username = Column('username', String(50), unique=True)

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return '<User %s>' % self.username


class CustomGraph(DatabaseObject):

    __tablename__ = 'custom_graph'
    __table_args__ = {'mysql_engine': 'InnoDB'}

    id         = Column('id', Integer, primary_key=True)
    title      = Column('title', String(50))
    user_id    = Column('user_id', Integer)
    timescale  = Column('timescale', String(10))
    fields     = Column('fields', Text)
    graph_type = Column('graph_type', String(20))
    ordering   = Column('ordering', Integer)

    def __init__(self, title, user_id, timescale, fields, ordering,
            graph_type=None):

        self.title = title
        self.user_id = user_id
        self.timescale = timescale
        self.fields = fields
        self.ordering = ordering
        self.graph_type = graph_type

    def __repr__(self):
        return '<CustomGraph %s %s>' % (self.title, self.user_id)


class Data(DatabaseObject):

    __tablename__ = 'data'

    id = Column('id', Integer, primary_key=True)
    component = Column('component', String(50), index=True)
    metric = Column('metric', String(50), index=True)
    last_updated = Column('last_updated', DateTime)

    data_6h = Column('data_6h', Text)
    data_36h = Column('data_36h', Text)
    data_1w = Column('data_1w', Text)
    data_1m = Column('data_1m', Text)
    data_6m = Column('data_6m', Text)

    index_6h = Column('index_6h', Integer)
    index_36h = Column('index_36h', Integer)
    index_1w = Column('index_1w', Integer)
    index_1m = Column('index_1m', Integer)
    index_6m = Column('index_6m', Integer)

    updates_since_6h_roll_up = Column('updates_since_6h_roll_up', Integer)
    updates_since_36h_roll_up = Column('updates_since_36h_roll_up', Integer)
    updates_since_1w_roll_up = Column('updates_since_1w_roll_up', Integer)
    updates_since_1m_roll_up = Column('updates_since_1m_roll_up', Integer)

    def __init__(self, component, metric):
        self.component = component
        self.metric = metric
        self.last_updated = self._get_time_slot()

        self._data_6h  = [0] * 360 # Every 1 min
        self._data_36h = [0] * 432 # Every 5 min
        self._data_1w  = [0] * 336 # Every 30 min
        self._data_1m  = [0] * 360 # Every 2 hours
        self._data_6m  = [0] * 360 # Every 12 hours

        self.data_6h = simplejson.dumps(self._data_6h)
        self.data_36h = simplejson.dumps(self._data_36h)
        self.data_1w = simplejson.dumps(self._data_1w)
        self.data_1m = simplejson.dumps(self._data_1m)
        self.data_6m = simplejson.dumps(self._data_6m)

        self.index_6h = 0
        self.index_36h = 0
        self.index_1w = 0
        self.index_1m = 0
        self.index_6m = 0

        self.updates_since_6h_roll_up = 0
        self.updates_since_36h_roll_up = 0
        self.updates_since_1w_roll_up = 0
        self.updates_since_1m_roll_up = 0

    def __repr__(self):
        return '<Data %s %s>' % (self.component, self.metric)

    def _get_time_slot(self):
        time_slot = int(time.time()) / 60 * 60
        return datetime.datetime.fromtimestamp(time_slot)

    def check_for_rollups(self):
        # If we need to do a rollup
        if self.updates_since_6h_roll_up >= 10:
            # Make sure we have self._data set
            if getattr(self, '_data_36h', None) is None:
                self._data_36h = simplejson.loads(self.data_36h)

            # Look at the past data set (may wrap around)
            start = self.index_6h - 10
            end = self.index_6h

            subset = []

            if start < 0:
                subset = self._data_6h[start+1:]
                subset.extend(self._data_6h[:end+1])
            else:
                subset = self._data_6h[start+1:end+1]

            # Find the min and max (and what order they are in)
            min_value = min(subset)
            min_index = subset.index(min_value)

            max_value = max(subset)
            max_index = subset.index(max_value)

            first_value = 0
            second_value = 0

            if min_index < max_index:
                first_value = min_value
                second_value = max_value
            else:
                first_value = max_value
                second_value = min_value

            # Save the two data points to the rollup
            self._data_36h[self.index_36h] = first_value
            self.index_36h += 1
            self.index_36h %= len(self._data_36h)
            self.updates_since_36h_roll_up += 1

            self._data_36h[self.index_36h] = second_value
            self.index_36h += 1
            self.index_36h %= len(self._data_36h)
            self.updates_since_36h_roll_up += 1

            # Save the rolled up data
            self.data_36h = simplejson.dumps(self._data_36h)

            self.updates_since_6h_roll_up -= 10

        # If we need to do a rollup
        if self.updates_since_36h_roll_up >= 12:
            # Make sure we have self._data set
            if getattr(self, '_data_1w', None) is None:
                self._data_1w = simplejson.loads(self.data_1w)

            # Look at the past data set (may wrap around)
            start = self.index_36h - 12
            end = self.index_36h

            subset = []

            if start < 0:
                subset = self._data_36h[start:]
                subset.extend(self._data_36h[:end])
            else:
                subset = self._data_36h[start:end]

            # Find the min and max (and what order they are in)
            min_value = min(subset)
            min_index = subset.index(min_value)

            max_value = max(subset)
            max_index = subset.index(max_value)

            first_value = 0
            second_value = 0

            if min_index < max_index:
                first_value = min_value
                second_value = max_value
            else:
                first_value = max_value
                second_value = min_value

            # Save the two data points to the rollup
            self._data_1w[self.index_1w] = first_value
            self.index_1w += 1
            self.index_1w %= len(self._data_1w)
            self.updates_since_1w_roll_up += 1

            self._data_1w[self.index_1w] = second_value
            self.index_1w += 1
            self.index_1w %= len(self._data_1w)
            self.updates_since_1w_roll_up += 1

            # Save the rolled up data
            self.data_1w = simplejson.dumps(self._data_1w)

            self.updates_since_36h_roll_up -= 12

        # If we need to do a rollup
        if self.updates_since_1w_roll_up >= 8:
            # Make sure we have self._data set
            if getattr(self, '_data_1m', None) is None:
                self._data_1m = simplejson.loads(self.data_1m)

            # Look at the past data set (may wrap around)
            start = self.index_1w - 8
            end = self.index_1w

            subset = []

            if start < 0:
                subset = self._data_1w[start:]
                subset.extend(self._data_1w[:end])
            else:
                subset = self._data_1w[start:end]

            # Find the min and max (and what order they are in)
            min_value = min(subset)
            min_index = subset.index(min_value)

            max_value = max(subset)
            max_index = subset.index(max_value)

            first_value = 0
            second_value = 0

            if min_index < max_index:
                first_value = min_value
                second_value = max_value
            else:
                first_value = max_value
                second_value = min_value

            # Save the two data points to the rollup
            self._data_1m[self.index_1m] = first_value
            self.index_1m += 1
            self.index_1m %= len(self._data_1m)
            self.updates_since_1m_roll_up += 1

            self._data_1m[self.index_1m] = second_value
            self.index_1m += 1
            self.index_1m %= len(self._data_1m)
            self.updates_since_1m_roll_up += 1

            # Save the rolled up data
            self.data_1m = simplejson.dumps(self._data_1m)

            self.updates_since_1w_roll_up -= 8

        # If we need to do a rollup
        if self.updates_since_1m_roll_up >= 12:
            # Make sure we have self._data set
            if getattr(self, '_data_6m', None) is None:
                self._data_6m = simplejson.loads(self.data_6m)

            # Look at the past data set (may wrap around)
            start = self.index_1m - 12
            end = self.index_1m

            subset = []

            if start < 0:
                subset = self._data_1m[start:]
                subset.extend(self._data_1m[:end])
            else:
                subset = self._data_1m[start:end]

            # Find the min and max (and what order they are in)
            min_value = min(subset)
            min_index = subset.index(min_value)

            max_value = max(subset)
            max_index = subset.index(max_value)

            first_value = 0
            second_value = 0

            if min_index < max_index:
                first_value = min_value
                second_value = max_value
            else:
                first_value = max_value
                second_value = min_value

            # Save the two data points to the rollup
            self._data_6m[self.index_6m] = first_value
            self.index_6m += 1
            self.index_6m %= len(self._data_6m)

            self._data_6m[self.index_6m] = second_value
            self.index_6m += 1
            self.index_6m %= len(self._data_1m)

            # Save the rolled up data
            self.data_6m = simplejson.dumps(self._data_6m)

            self.updates_since_1m_roll_up -= 12

    def update(self, value, time_slot=None):
        if getattr(self, '_data_6h', None) is None:
            self._data_6h = simplejson.loads(self.data_6h)

        if time_slot is None:
            time_slot = self._get_time_slot()

        if time_slot == self.last_updated:
            self._data_6h[self.index_6h] = value

        else:
            while self.last_updated < time_slot:
                self.last_updated += datetime.timedelta(seconds=60)

                self.index_6h += 1
                self.index_6h %= len(self._data_6h)

                if self.last_updated == time_slot:
                    self._data_6h[self.index_6h] = value
                else:
                    self._data_6h[self.index_6h] = 0

                self.updates_since_6h_roll_up += 1

                self.check_for_rollups()

        self.data_6h = simplejson.dumps(self._data_6h)

    def get_data(self, timescale='6h'):
        '''Other timescales: 36h, 1w, 1m, 6m'''
        should_save = False

        if getattr(self, '_data_6h', None) is None:
            self._data_6h = simplejson.loads(self.data_6h)

        # Data might not yet be sent for this minute
        time_slot = self._get_time_slot() - datetime.timedelta(seconds=60)

        while self.last_updated < time_slot:
            should_save = True

            self.last_updated += datetime.timedelta(seconds=60)

            self.index_6h += 1
            self.index_6h %= len(self._data_6h)

            self._data_6h[self.index_6h] = 0

            self.updates_since_6h_roll_up += 1

            self.check_for_rollups()

        if should_save:
            self.data_6h = simplejson.dumps(self._data_6h)

        array = self._data_6h
        index = self.index_6h + 1
        index %= len(self._data_6h)

        if timescale == '36h':
            if getattr(self, '_data_36h', None) is None:
                self._data_36h = simplejson.loads(self.data_36h)

            array = self._data_36h
            index = self.index_36h

        elif timescale == '1w':
            if getattr(self, '_data_1w', None) is None:
                self._data_1w = simplejson.loads(self.data_1w)

            array = self._data_1w
            index = self.index_1w

        elif timescale == '1m':
            if getattr(self, '_data_1m', None) is None:
                self._data_1m = simplejson.loads(self.data_1m)

            array = self._data_1m
            index = self.index_1m

        elif timescale == '6m':
            if getattr(self, '_data_6m', None) is None:
                self._data_6m = simplejson.loads(self.data_6m)

            array = self._data_6m
            index = self.index_6m

        before = array[index:]
        after = array[:index]

        before.extend(after)

        return before, should_save
