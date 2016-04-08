#!/home/davec/envs/datamodel/bin/python

# from django.conf import settings
from cassandra import cqlengine
from cassandra.cqlengine import columns
from cassandra.auth import PlainTextAuthProvider
from cassandra.cqlengine.models import Model
import subprocess
import os
# import sys
import re


def description_file(*path):
    file_path  = os.path.join('description',*path) + '.txt'
    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))

    if not os.path.exists(file_path):
        with open(file_path,'w') as d:
            d.write("no description yet in "+file_path+" :( ")

    with open(file_path,'r') as f:
        return ''.join(f.readlines())


class SchemaKeyspaces(Model):
    __keyspace__     = 'system'
    keyspace_name    = columns.Text(primary_key=True)
    durable_writes   = columns.Boolean()
    strategy_class   = columns.Text()
    strategy_options = columns.Text()

    def description(self):
        return description_file(self.keyspace_name)

    def schema_columnfamilies(self):
        return SchemaColumnfamilies.objects.filter(keyspace_name=self.keyspace_name)

    def schema_columnfamily(self,name):
        return SchemaColumnfamilies.objects.filter(keyspace_name=self.keyspace_name,columnfamily_name=name)


class SchemaColumnfamilies(Model):
    __keyspace__     = 'system'

    keyspace_name                   = columns.Text(primary_key=True)
    columnfamily_name               = columns.Text(primary_key=True)
    bloom_filter_fp_chance          = columns.Double()
    caching                         = columns.Text()
    cf_id                           = columns.UUID()
    column_aliases                  = columns.Text()
    comment                         = columns.Text()
    compaction_strategy_class       = columns.Text()
    compaction_strategy_options     = columns.Text()
    comparator                      = columns.Text()
    compression_parameters          = columns.Text()
    default_time_to_live            = columns.Integer()
    default_validator               = columns.Text()
    dropped_columns                 = columns.Map(key_type=columns.Text,value_type=columns.Integer)
    gc_grace_seconds                = columns.Integer()
    index_interval                  = columns.Integer()
    is_dense                        = columns.Boolean()
    key_aliases                     = columns.Text()
    key_validator                   = columns.Text()
    local_read_repair_chance        = columns.Double()
    max_compaction_threshold        = columns.Integer()
    max_index_interval              = columns.Integer()
    memtable_flush_period_in_ms     = columns.Integer()
    min_compaction_threshold        = columns.Integer()
    min_index_interval              = columns.Integer()
    read_repair_chance              = columns.Double()
    speculative_retry               = columns.Text()
    subcomparator                   = columns.Text()
    type                            = columns.Text()
    value_alias                     = columns.Text()

    def description(self):
        return description_file(self.keyspace_name,self.columnfamily_name)

    def schema_columns(self):
        return sorted(SchemaColumns.objects.filter(keyspace_name=self.keyspace_name,columnfamily_name=self.columnfamily_name))

    def cfhistograms(self):
        return subprocess.Popen(['nodetool', '--username', 'development', '--password', 'xxxx',
                                'cfhistograms', self.keyspace_name, self.columnfamily_name],
                                stdout=subprocess.PIPE).communicate()[0]

    def cfstats(self):
        return subprocess.Popen(['nodetool', '--username', 'development', '--password', 'xxxx',
                                'cfstats', self.keyspace_name+'.'+self.columnfamily_name, '-H'],
                                stdout=subprocess.PIPE).communicate()[0]

schema_column_cache = None


class SchemaColumns(Model):
    __keyspace__   = 'system'

    keyspace_name       = columns.Text(primary_key=True)
    columnfamily_name   = columns.Text(primary_key=True)
    column_name         = columns.Text(primary_key=True)
    component_index     = columns.Integer()                 # 0,1... for composite keys
    index_name          = columns.Text()
    index_options       = columns.Text()
    index_type          = columns.Text()
    type                = columns.Text()
    validator           = columns.Text()

    def description(self):
        return description_file(self.keyspace_name,self.columnfamily_name,self.column_name)

    def field_type(self):
        return re.sub(r'Type', '', re.sub( r'org.apache.cassandra.db.marshal.', '', self.validator))

    def key(self):
        key = ''
        if self.type == 'partition_key':
            key = 'P'+str(self.component_index or 0)
        elif self.type == 'clustering_key':
            key = 'C'+str(self.component_index or 0)
        elif self.type == 'static':
            key = 's'
        if self.index_name:
            key += ' '+str(self.index_name)
        return key

    def __cmp__(self,other):
        """ Sort columns: partition keys, cluster keys, then alphabetical order
        """
        return ((other.type == 'partition_key')  - (self.type == 'partition_key')) \
            or ((other.type == 'static') - (self.type == 'static')) \
            or ((other.type == 'clustering_key') - (self.type == 'clustering_key')) \
            or ((other.index_name is not None)   - (self.index_name is not None)) \
            or (other.column_name < self.column_name)

    def also_in(self):
        """
            Find other columnfamilies with an identically named column
        """
        global schema_column_cache
        if not schema_column_cache:
            schema_column_cache = list(SchemaColumns.objects.all())
        return [(c.keyspace_name,c.columnfamily_name) for c in schema_column_cache
                if c.column_name == self.column_name and c.columnfamily_name != self.columnfamily_name]


class Table(object):
    def __init__(self, keyspace_name, columnfamily_name):
        self.keyspace_name         = keyspace_name
        self.columnfamily_name     = columnfamily_name
        self.id                    = (keyspace_name,columnfamily_name)
        self.name                  = keyspace_name+'.'+columnfamily_name
        self.pk                    = []
        self.cols                  = []
        self.references            = []
        self.referenced_by         = []
        self.one_to_one            = []
        self.multi_valued_atts     = []
        self.nodes                 = []
        self.edges                 = []
        self.related_node(self)

    def get_node(self):
        return {'id':self.name,'label':self.name,'color':'#FF8888'}

    def related_node(self,table,to_arrow=False,from_arrow=False):
        self.nodes.append(table.get_node())
        if to_arrow:
            self.edges.append({'from':self.name, 'to':table.name, 'arrows':'to'})
            self.references.append(table.id)
        if from_arrow:
            self.edges.append({'from':table.name, 'to':self.name, 'arrows':'from'})
            table.referenced_by.append(self.id)

    def references_table(self,other_table):
        # if different column family and same keyspace and
        # table_2 columns includes table_1 partition_key
        # then we have a potential match!
        if other_table == self or other_table.keyspace_name != self.keyspace_name:
            return False
        if other_table.pk == [u'date']:
            return False
        return set(other_table.pk).issubset(self.cols)

    def add_column(self,c):
        if c.type == 'partition_key' or c.type == 'cluster_key':
            self.pk.append(c.column_name)
        self.cols.append(c.column_name)

        if c.validator.startswith('org.apache.cassandra.db.marshal.Map') or \
           c.validator.startswith('org.apache.cassandra.db.marshal.List') or \
           c.validator.startswith('org.apache.cassandra.db.marshal.Set'):

            # Hack for all the client_* fields in scraped_infringements
            col_name = c.column_name
            if col_name.startswith('client'):
                col_name = 'CLIENTS_*'
            if col_name not in self.multi_valued_atts:
                self.multi_valued_atts.append(col_name)
                self.nodes.append({'id': col_name, 'label': col_name, 'color':'#00AA00'})
                self.edges.append({'from':self.name, 'to': col_name})


class Schema(object):
    """
        Cassandra schema contains multiple keyspaces
    """
    keyspaces = None
    full_schema = None

    def __init__(self):
        cqlengine.connection.setup(['localhost'],'system', auth_provider=PlainTextAuthProvider(username='development',password='xxxx'))
        self.make_full_schema()

    def schema_keyspaces(self):
        if not self.keyspaces:
            self.keyspaces = SchemaKeyspaces.objects.all()
        return self.keyspaces

    def schema_keyspace(self,name):
        return [ks for ks in self.schema_keyspaces() if ks.keyspace_name == name][0]

    def make_full_schema(self):
        #
        # Build a full schema mapping
        # - build a list of all tables
        # - assume foreign key if same keyspace and table_1 partition key is subset of table_2 columns
        # - assume overnormalisation if tables have same partition key
        # - model multi-valued attributes (lists, map, set) as subentity.
        #
        if not self.full_schema:
            self.full_schema = {}
            self.all_edges = []
            self.all_nodes = []

            for c in SchemaColumns.objects.all():
                if not (c.keyspace_name,c.columnfamily_name) in self.full_schema:
                    table = Table(c.keyspace_name,c.columnfamily_name)
                    self.full_schema[(c.keyspace_name,c.columnfamily_name)] = table
                table.add_column(c)

            for table_1 in self.full_schema.values():
                self.all_nodes.append( table_1.get_node())
                for table_2 in self.full_schema.values():
                    if table_2.references_table(table_1):
                        if table_1.pk == table_2.pk:
                            if table_1.id > table_2.id:
                                table_1.one_to_one.append(table_2.id)
                                table_1.related_node( table_2, to_arrow=True, from_arrow=True)
                                self.all_edges.append({'from':table_1.name, 'to': table_2.name, 'arrows':'to,from'})
                        else:
                            table_1.related_node(table_2)
                            table_2.related_node(table_1)
                            self.all_edges.append({'from':table_1.name, 'to':table_2.name})

    def get_table(self,keyspace_name,columnfamily_name):
        if not self.full_schema:
            self.make_full_schema()
        return self.full_schema[keyspace_name,columnfamily_name]

    def nodes(self,keyspace_name,columnfamily_name=None):
        if columnfamily_name:
            return self.get_table(keyspace_name,columnfamily_name).nodes
        else:
            return [n for n in self.all_nodes if n['id'].startswith(keyspace_name)]

    def edges(self,keyspace_name,columnfamily_name=None):
        if columnfamily_name:
            return self.get_table(keyspace_name,columnfamily_name).edges
        else:
            return self.all_edges

if __name__ == '__main__':
    cqlengine.connection.setup(['localhost'],'system', auth_provider=PlainTextAuthProvider(username='development',password='xxxx'))
    s = Schema()
