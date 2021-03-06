#!/usr/bin/python
# -*- coding: utf-8 -
import requests
import paho.mqtt.publish as publish
import argparse
import logging
import urlparse
import datetime
from jinja2 import Environment


def datetimeformat(value, format='%d-%m-%Y %H:%M:%s'):
    return value.strftime(format)


def todatetime(value):
    return datetime.datetime.fromtimestamp(int(value))


def main():
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument("-u", "--url", required=True)
    parser.add_argument("-m", "--mqtt", default="localhost:1883", type=urlparse.urlparse)
    parser.add_argument("-r", "--retain", action="store_true", default=False)
    parser.add_argument("-v", action="store_true", default=False, help="Verbose logging", dest="verbose")
    parser.add_argument("-t", "--topic", action="append", nargs=2)
    parser.add_argument("--logfile", help="Logging into file")
    args = parser.parse_args()

    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                        level=logging.DEBUG if args.verbose else logging.INFO, filename=args.logfile)

    params = {'auth': None if args.mqtt.username is None else {'username': args.mqtt.username,
                                                               'password': args.mqtt.password},
              'hostname': args.mqtt.hostname,
              'port': 1883 if args.mqtt.port is None else args.mqtt.port,
              'retain': args.retain}

    jinja = Environment(extensions=['jinja2.ext.do'])
    jinja.filters['datetimeformat'] = datetimeformat
    jinja.filters['todatetime'] = todatetime

    req = requests.get(args.url)
    logging.debug(req.text)
    data = req.json()

    for item in args.topic:
        topic, template = item
        template = jinja.from_string(template)
        payload = template.render(response=data)

        params.update({'topic': topic, 'payload': payload})
        logging.info("%s: %s", topic, payload)
        publish.single(**params)


if __name__ == '__main__':
    main()
