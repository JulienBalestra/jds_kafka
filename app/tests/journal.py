APPEND = 1


class Reader(object):
	def __init__(self, *args, **kwargs):
		pass

	def seek_cursor(self, cursor):
		pass

	def get_next(self):
		pass

	def __iter__(self):
		yield {"__CURSOR": "abc"}

	def get_events(self):
		pass

	def process(self):
		pass

	def close(self):
		pass
