#!/home/davec/schema/venv/bin/python

import os
import sys
import re

class_def = {}
class_re  = re.compile( r'class (?P<class_name>\w+)\((?P<parents>[^\)]+)\):' )
	#                         class SomeClassName ( List,of,Parents )
table_re  = re.compile( r".*__table_name__ = ['\"](?P<table_name>\w+)['\"]" )

	#                         class SomeClassName ( List,of,Parents )

class Classes(object):

	def __init__( self ):
		for root,dirs,files in os.walk('../src'):
			for file in files:
				if not file.endswith('.py'):
					continue

				path = os.path.join(root,file)

				with open( path ) as f:
					class_name = ''
					for i,line in enumerate(f.readlines()):
						m = class_re.match(line)
						if m:
							for parent in m.group('parents').split(','):
								parent_class_name = parent.strip().split('.')[-1]
								class_name = m.group('class_name')

								#print class_name, parent_class_name

								if not class_name in class_def:
									class_def[class_name] = {
										'name':    class_name,
										'source':  path+":"+str(i),
										'parents': set(),
										'code':    line[:-1],
										'table_name': '',
									 }

								class_def[class_name]['parents'].add(parent_class_name)
							continue
						
						if class_name:
							m = table_re.match(line)
							if m:
								class_def[class_name]['table_name'] = m.group('table_name')

	def show(self):
		all_sorted = {}
		for child in class_def.values():
			for branch in self.ancestors( child ):
				path =  ",".join(branch)
				x = {'ancestors': list(branch)}
				x.update(child)
				all_sorted[path] = x

		return [ all_sorted[path]['source'] + "<br><b>" + "\nIS_A ".join(all_sorted[path]['ancestors']) + "</b><br>" for path in sorted(all_sorted) ]



	def ancestors(self,child):
		#print "ancestors", child

		if not child['parents']:
			yield [ child['name'] + " (NO PARENT)" ]
			return

		for parent_name in child['parents']:
			if not parent_name in class_def:
				yield [ child['name'] + " (NO DEFINITION)" ]
				continue

			if child['name'] == class_def[parent_name]['name']:
				yield [ child['name'] + " (RECURSIVE CLASSNAME - STOP)" ]
				continue

			for ancestor_name in self.ancestors(class_def[parent_name]):
				if child['table_name']:
					yield [ child['name'] + " (TABLE: " + child['table_name'] + ") " ] + ancestor_name
				else:
					yield [ child['name'] ] + ancestor_name

if __name__ == '__main__':
    c = Classes()
    print "\n".join( c.show() )
