import logging
import argparse
import paho.mqtt.client as mqtt
import urlparse
import inotify.adapters
import inotify.constants
import re
import yaml
import json


class Feed(object):
    def __init__(self, file, topic, states, mqttc, watcher):
        self.file = file
        self.topic = topic
        self.templates = {state: re.compile(regexp) for state, regexp in states.items()}
        self.fd = None
        self.wd = None
        self.states = {}
        self.mqttc = mqttc
        self.watcher = watcher
        pass

    def reopen(self):
        if self.fd is not None:
            self.fd.close()
        self.fd = open(self.file, "r")

        if self.watcher is None:
            return

        if self.wd is not None:
            self.watcher.remove_watch_with_id(self.wd)

        self.wd = self.watcher.add_watch(
            self.file,
            mask=inotify.constants.IN_MODIFY | inotify.constants.IN_MOVE_SELF
        )

    def trigger(self, topic, state):
        self.states[topic] = state
        logging.info("Sensor %s changed state to %d" % (topic, state))
        if self.mqttc is not None:
            self.mqttc.notify(topic, state)
        pass

    def process(self):
        data = self.fd.read()
        for line in data.strip().split("\n"):
            self.process_line(line.strip())
        pass

    def process_line(self, line):
        logging.debug(line)

        for current_state, regexp in self.templates.items():
            match = regexp.match(line)
            if match is not None:
                topic = match.expand(self.topic)
                if self.states.get(topic) != current_state:
                    self.states[topic] = current_state
                    self.trigger(topic, current_state)
        pass


class Application(object):

    def __init__(self):
        self.config = {}
        self.feeds = []
        self.args = None
        self.watcher = inotify.adapters.Inotify()

        self.load_config()
        logging.captureWarnings(True)
        logging.basicConfig(
            format=u'%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s',
            level=logging.DEBUG if self.config['debug'] else logging.INFO,
            filename=self.config['logfile']
        )
        logging.debug("Loaded configuration: %s", json.dumps(self.config, indent=2, skipkeys=True, default=str))

    def on_mqtt_connect(self, client, userdata, flags, rc):
        logging.info("Connection to MQTT broker: %s", mqtt.connack_string(rc))
        pass

    def load_config(self):
        parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
        parser.add_argument("-c", "--config", type=file, help="Load config from file")
        parser.add_argument("--url")
        parser.add_argument("--all", action="store_true", default=False)
        parser.add_argument("-v", action="store_true", help="Verbose logging", dest="debug")
        parser.add_argument("--logfile", help="Logging into file")

        args = parser.parse_args()

        self.config = {'url': 'mqtt://localhost:1883', 'logfile': None, 'input': []}
        self.config.update(yaml.load(args.config, yaml.Loader))
        self.config.update({k: v for k, v in vars(args).items() if v})

        self.feeds = [Feed(mqttc=self, watcher=self.watcher, **x) for x in self.config['input']]

    def get_feed_by_watch(self, wd):
        for feed in self.feeds:
            if feed.wd == wd:
                return feed

    def run(self):
        url = urlparse.urlparse(self.config['url'])

        logging.info("Trying connect to MQTT broker at %s:%d" % (url.hostname, url.port))
        self.mqttc = mqtt.Client()

        if url.username is not None:
            self.mqttc.username_pw_set(url.username, url.password)

        self.mqttc.on_connect = self.on_mqtt_connect
        self.mqttc.connect(url.hostname, url.port if url.port is not None else 1883, 60)
        self.mqttc.loop_start()

        for feed in self.feeds:
            feed.reopen()
            if self.config.get('all', False):
                feed.process()
            feed.fd.read()

        # Wait and process inotify events
        while True and self.watcher:
            for event in self.watcher.event_gen(yield_nones=False):
                (header, type_names, path, filename) = event
                feed = self.get_feed_by_watch(header.wd)
                if feed is not None:
                    if 'IN_MOVE_SELF' in type_names:
                        feed.reopen()
                    if 'IN_MODIFY' in type_names:
                        feed.process()
    pass


def main():
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
