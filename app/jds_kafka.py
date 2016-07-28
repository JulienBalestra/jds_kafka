#! /usr/bin/env python
import argparse
import json
import os
import time

try:
	from systemd import journal
except ImportError:
	if os.getenv("SD") == "no":
		from tests import journal
	else:
		raise ImportError("from systemd import journal")

from kafka import KafkaProducer


def _convert_trivial(x):
	return x


def _convert_monotonic(x):
	return x[0]


BASIC_CONVERTERS = {
	'MESSAGE_ID': _convert_trivial,
	'_MACHINE_ID': _convert_trivial,
	'_BOOT_ID': _convert_trivial,
	'_SOURCE_REALTIME_TIMESTAMP': _convert_trivial,
	'__REALTIME_TIMESTAMP': _convert_trivial,
	'_SOURCE_MONOTONIC_TIMESTAMP': _convert_monotonic,
	'__MONOTONIC_TIMESTAMP': _convert_monotonic
}

SINCE_DB = "./sincedb"


class JournaldStream(object):
	messages_steps = 100
	logs_topic_name = "logs"
	kafka_sleep = 1

	def __init__(self, kafka_hosts, journal_path="/run/log/journal"):
		self.kafka_hosts = self._force_type_value(list, kafka_hosts)

		self.producer = KafkaProducer(
				bootstrap_servers=self.kafka_hosts,
				value_serializer=lambda v: json.dumps(v).encode('utf-8'))

		self.reader = journal.Reader(path=journal_path, converters=BASIC_CONVERTERS)
		self.cursor = ""
		self.read_messages = 0
		self.key_filters = self._build_key_filters()
		self.value_filters = lambda x: x

	@staticmethod
	def _build_key_filters():

		def remove_prefix(key, prefix="_"):
			new = key
			while new[0] == prefix:
				new = new[1:]
			return new

		def lower_key(key):
			return key.lower()

		def aggregate_filters(key):
			for f in [remove_prefix, lower_key]:
				key = f(key)
			return key

		return aggregate_filters

	@staticmethod
	def _force_type_value(type_want, variable):
		assert type_want is type(variable)
		return variable

	def _save_cursor(self):
		if self.cursor != "":
			with open(SINCE_DB, 'w') as f:
				f.write(self.cursor)
		else:
			os.write(2, "invalid cursor\n")

	def _get_cursor(self):
		try:
			with open(SINCE_DB, 'r') as f:
				self.cursor = f.read()
				return True if self.cursor else False
		except IOError:
			return False

	def _stream_to_seek(self):
		if self._get_cursor():
			os.write(1, "using saved cursor \"%s\"\n" % self.cursor)
			self.reader.seek_cursor(self.cursor)
			self.reader.get_next()
		else:
			os.write(1, "using new cursor\n")

		for log in self.reader:
			self._kafka_send(log)

		os.write(1, "seeked journal after %d messages\n" % self.read_messages)

	def _stream_poller(self):
		i = 0
		os.write(1, "start polling realtime messages\n")
		while self.reader.get_events():
			i += 1
			if self.reader.process() == journal.APPEND:
				for log in self.reader:
					self._kafka_send(log)
			else:
				time.sleep(self.kafka_sleep)
			self._periodic_sleep_task(i)

	def stream(self):
		self._stream_to_seek()
		self._stream_poller()

	def _periodic_send_task(self):
		if self.read_messages % self.messages_steps == 0:
			os.write(1, "read %d messages, process flush\n" % self.read_messages)
			ts = time.time()
			self.producer.flush()
			os.write(1, "flush done in %d\n" % (time.time() - ts))

	@staticmethod
	def _periodic_sleep_task(nb_message):
		pass

	def _filters(self, full_log):
		# Keys
		filter_data = {self.key_filters(k): self.value_filters(v) for k, v in full_log.iteritems()}

		# Values
		# Handle by BASIC_CONVERTERS Journal builtin

		return filter_data

	def _kafka_send(self, full_log):
		filter_data = self._filters(full_log)
		self.producer.send(self.logs_topic_name, filter_data)
		self.cursor = full_log["__CURSOR"]
		self._save_cursor()
		self.read_messages += 1
		self._periodic_send_task()

	def close(self):
		os.write(1, "closing journald.Reader\n")
		self.reader.close()
		os.write(1, "closing kafka connection\n")
		self.producer.close()


def comma_list(string):
	return string.split(',')


def fast_arg_parsing():
	args = argparse.ArgumentParser()
	args.add_argument("kafka_hosts", type=comma_list,
					  help="Kafka hosts \"HOST:PORT,HOST:PORT\" or HOST:PORT")

	args.add_argument("--sincedb_path", type=str, default="/run/log/journal/sincedb",
					  help="SinceDB path for Journald cursor")

	return args.parse_args().kafka_hosts, args.parse_args().sincedb_path


if __name__ == "__main__":
	hosts, SINCE_DB = fast_arg_parsing()
	print "hosts: %s sincedb: %s" % (hosts, SINCE_DB)
	js = JournaldStream(hosts)
	try:
		js.stream()
	except KeyboardInterrupt:
		js.close()
		print "gracefully close, read %d messages" % js.read_messages
