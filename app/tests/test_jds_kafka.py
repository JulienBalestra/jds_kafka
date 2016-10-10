#! /usr/bin/env python
import os

from app import jds_kafka

import unittest


class TestFilterKey(unittest.TestCase):
    def test_00_filter_key(self):
        key = jds_kafka.JournaldStream._build_key_filters()
        self.assertEqual("cursor", key("__CURSOR"))

    def test_01_filter_key(self):
        key = jds_kafka.JournaldStream._build_key_filters()
        self.assertEqual("slice", key("_SLICE"))

    def test_02_filter_key(self):
        key = jds_kafka.JournaldStream._build_key_filters()
        self.assertEqual("message", key("MESSAGE"))

    def test_03_filter_key(self):
        key = jds_kafka.JournaldStream._build_key_filters()
        self.assertEqual("timestamp", key("timestamp"))


class DummyKafka(object):
    def __init__(self, *args, **kwargs):
        self.messages = {}

    def send(self, topic, data):
        assert type(topic) == str
        assert type(data) == dict
        self.messages[topic] = data

    def close(self):
        pass

    def flush(self):
        raise NotImplementedError


class TestCommaList(unittest.TestCase):
    def test_00(self):
        self.assertEqual(['a', 'b', 'c'], jds_kafka.comma_list("a,b,c"))


class TestJournaldStream(unittest.TestCase):
    jds = jds_kafka.JournaldStream

    @classmethod
    def setUpClass(cls):
        jds_kafka.KafkaProducer = DummyKafka
        cls.jds = jds_kafka.JournaldStream(["ip_address"])
        if os.path.isfile(jds_kafka.SINCEDBPATH):
            os.remove(jds_kafka.SINCEDBPATH)

    @classmethod
    def tearDownClass(cls):
        if os.path.isfile(jds_kafka.SINCEDBPATH):
            os.remove(jds_kafka.SINCEDBPATH)

    def test_00_filters(self):
        r = self.jds._filters({"__CURSOR": "abc"})
        self.assertEqual({"cursor": "abc"}, r)

    def test_01_filters(self):
        real = {
            "__CURSOR": "s=7c475f24180d47188aa7a1e3c053d440;i=c8a202;b=9938f016835e4aa6a9523b4100e2fafd;m=39ca5092898;t=5386df79bfefc;x=6ba5d133c30aeefa",
            "__REALTIME_TIMESTAMP": "1469419840339708",
            "__MONOTONIC_TIMESTAMP": "3971318622370",
            "_BOOT_ID": "9938f016835e4aa6a9523b4100e2fafd",
            "_TRANSPORT": "syslog",
            "PRIORITY": "5",
            "SYSLOG_FACILITY": "3",
            "SYSLOG_IDENTIFIER": "multipathd",
            "_PID": "2500",
            "_UID": "0",
            "_GID": "0",
            "_COMM": "multipathd",
            "_EXE": "/usr/sbin/multipathd",
            "_CMDLINE": "/sbin/multipathd",
            "_CAP_EFFECTIVE": "1fffffffff",
            "_SYSTEMD_CGROUP": "/system.slice/multipathd.service",
            "_SYSTEMD_UNIT": "multipathd.service",
            "_SYSTEMD_SLICE": "system.slice",
            "_SELINUX_CONTEXT": "system_u:system_r:lvm_t:s0",
            "_MACHINE_ID": "1af51fd8de8e4de18d08c511e026c1e7",
            "_HOSTNAME": "hostname",
            "MESSAGE": "message logger",
            "_SOURCE_REALTIME_TIMESTAMP": "1469419840339280"
        }
        expect = {'hostname': 'hostname',
                  'uid': '0',
                  'realtime_timestamp': '1469419840339708',
                  'pid': '2500',
                  'syslog_facility': '3',
                  'cmdline': '/sbin/multipathd',
                  'message': 'message logger',
                  'transport': 'syslog',
                  'source_realtime_timestamp': '1469419840339280',
                  'cap_effective': '1fffffffff',
                  'priority': '5',
                  'gid': '0',
                  'systemd_unit': 'multipathd.service',
                  'syslog_identifier': 'multipathd',
                  'comm': 'multipathd',
                  'monotonic_timestamp': '3971318622370',
                  'systemd_slice': 'system.slice',
                  'exe': '/usr/sbin/multipathd',
                  'cursor': 's=7c475f24180d47188aa7a1e3c053d440;i=c8a202;b=9938f016835e4aa6a9523b4100e2fafd;m=39ca5092898;t=5386df79bfefc;x=6ba5d133c30aeefa',
                  'boot_id': '9938f016835e4aa6a9523b4100e2fafd',
                  'machine_id': '1af51fd8de8e4de18d08c511e026c1e7',
                  'systemd_cgroup': '/system.slice/multipathd.service',
                  'selinux_context': 'system_u:system_r:lvm_t:s0'}

        r = self.jds._filters(real)
        self.assertEqual(expect, r)

    def test_02_get_cursor(self):
        self.assertFalse(self.jds.cursor)
        self.jds._get_cursor()
        self.assertFalse(self.jds.cursor)

    def test_03_save_cursor(self):
        self.assertFalse(self.jds.cursor)
        self.jds._save_cursor()
        self.assertFalse(os.path.isfile(jds_kafka.SINCEDBPATH))

    def test_04_get_cursor(self):
        self.assertFalse(self.jds.cursor)
        with open(jds_kafka.SINCEDBPATH, 'w') as f:
            f.write("s=abc")
        self.jds._get_cursor()
        self.assertEqual("s=abc", self.jds.cursor)

    def test_05_save_cursor(self):
        self.jds._save_cursor()
        self.assertTrue(os.path.isfile(jds_kafka.SINCEDBPATH))

    def test_all(self):
        if os.getenv("SD") != "NO":
            os.remove(jds_kafka.SINCEDBPATH)
            self.jds._stream_poller = lambda: None
        try:
            self.jds.stream()
            self.jds._periodic_send_task()
        except NotImplementedError:
            pass

        self.jds.close()
        if os.getenv("SD") == "NO":
            self.assertEqual({'logs': {'cursor': 'abc'}}, self.jds.producer.messages)


if __name__ == "__main__":
    unittest.main()
