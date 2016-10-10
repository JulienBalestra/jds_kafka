#! /usr/bin/env python
import argparse
import json
import os
import time

from kafka import KafkaProducer

if os.getenv("SD") == "no":
    from tests import journal

    pass  # for IDE features
else:
    from systemd import journal


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

SINCEDBPATH = os.getenv("SINCEDBPATH", "./sincedb")
JOURNALDPATH = os.getenv("JOURNALDPATH", "/run/log/journal")

KAFKA_HOSTS = os.getenv("KAFKA_HOSTS").split(",")


class JournaldStream(object):
    messages_steps = 100
    logs_topic_name = "logs"
    kafka_sleep = 1

    def __init__(self, kafka_hosts, journald_path, sincedb_path):

        # Sincedb is a file where the __CURSOR of Journald is stored
        self.sincedb_path = self._force_type_value(str, sincedb_path)
        self._read_or_create_sincedb(self.sincedb_path)

        # /run/log/journal
        self.journald_path = self._force_type_value(str, journald_path)
        self._is_journal_dir(self.journald_path)
        self.reader = journal.Reader(path=self.journald_path, converters=BASIC_CONVERTERS)

        # Kafka hosts
        self.kafka_hosts = self._force_type_value(list, kafka_hosts)
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_hosts,
            value_serializer=lambda v: json.dumps(v))

        self.cursor = ""
        self.read_messages = 0
        self.key_filters = self._build_key_filters()
        self.value_filters = lambda x: x

    @staticmethod
    def _read_or_create_sincedb(sincedb_path):
        if os.path.isfile(sincedb_path):
            with open(sincedb_path, 'r') as db:
                db.read()
        else:
            with open(sincedb_path, "w") as empty_db:
                empty_db.write("")

    @staticmethod
    def _is_journal_dir(journald_path):
        if not os.path.isdir(journald_path):
            raise IOError("%s not here" % journald_path)

    @staticmethod
    def _build_key_filters():
        """
        Transform the keys of a dict
        :return: list of functions
        """

        def remove_prefix(key, prefix="_"):
            """
            Journald create keys with '_', '__' prefix
            :param key:
            :param prefix:
            :return: Key reformatted
            """
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
        """
        Raise TypeError is the type is not matching
        :param type_want:
        :param variable:
        :return: variable
        """
        if type_want is not type(variable):
            raise TypeError("%s is not type(%s)" % (type_want, type(variable)))

        return variable

    def _save_cursor(self):
        if self.cursor != "":
            with open(self.sincedb_path, 'w') as f:
                f.write(self.cursor)
        else:
            os.write(2, "invalid cursor\n")

    def _get_cursor(self):
        try:
            with open(self.sincedb_path, 'r') as f:
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
            self._periodic_stream_task(i)

    def stream(self):
        """
        Public method
        """
        self._stream_to_seek()
        self._stream_poller()

    def _periodic_send_task(self):
        if self.read_messages % self.messages_steps == 0:
            os.write(1, "read %d messages, process flush\n" % self.read_messages)
            ts = time.time()
            self.producer.flush()
            os.write(1, "flush done in %d\n" % (time.time() - ts))

    @staticmethod
    def _periodic_stream_task(nb_message):
        pass

    def _filters(self, full_log):
        # Keys
        filter_data = {self.key_filters(k): self.value_filters(v) for k, v in full_log.iteritems()}

        # Values
        # Handle by BASIC_CONVERTERS Journal builtin

        return filter_data

    def _kafka_send(self, full_log):
        # Transform the log
        filter_data = self._filters(full_log)

        # Send it to Kafka
        self.producer.send(self.logs_topic_name, filter_data)

        # Save the cursor
        self.cursor = full_log["__CURSOR"]
        self._save_cursor()

        # Internal instance stats
        self.read_messages += 1
        self._periodic_send_task()

    def close(self):
        os.write(1, "closing journald.Reader\n")
        self.reader.close()
        os.write(1, "closing kafka connection\n")
        self.producer.close()


def comma_list(string):
    return string.split(',')


if __name__ == "__main__":
    jds = JournaldStream(KAFKA_HOSTS, JOURNALDPATH, SINCEDBPATH)
    try:
        jds.stream()
    except KeyboardInterrupt:
        jds.close()
        print "gracefully close, read %d messages" % jds.read_messages
