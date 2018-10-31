import logging
import argparse
import paho.mqtt.client as mqtt
import shlex
import urlparse
import inotify.adapters
import inotify.constants
import re

sensors_dict = {}

def on_mqtt_connect(client, userdata, flags, rc):
    logging.info("Connection to MQTT broker: %s", mqtt.connack_string(rc) )
    pass

def main():
    class LoadFromFile( argparse.Action ):
        def __call__ (self, parser, namespace, values, option_string = None):
           with values as f:
               parser.parse_args( shlex.split(f.read()), namespace )

    parser = argparse.ArgumentParser( fromfile_prefix_chars='@' )
    parser.add_argument( "-c", "--config", type=open, action=LoadFromFile, help="Load config from file" )
    parser.add_argument( "-u", "--url", default="mqtt://localhost:1883", type=urlparse.urlparse )
    parser.add_argument( "--prefix", default="/logsensors" )

    parser.add_argument( "--all", action="store_true", default=False)
    parser.add_argument( "-i", "--input" )
    parser.add_argument( "--on", type=re.compile )
    parser.add_argument( "--off", type=re.compile )

    parser.add_argument( "-v", action="store_true", default=False, help="Verbose logging", dest="verbose" )
    parser.add_argument( "--logfile", help="Logging into file" )
    args = parser.parse_args()

    # configure logging
    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",  level= logging.DEBUG if args.verbose else logging.INFO, filename=args.logfile )
    # mqtt broker
    logging.debug("Trying connect to MQTT broker at %s:%d" % (args.url.hostname, args.url.port) )

    mqttc = mqtt.Client()
    if args.url.username!=None:
        mqttc.username_pw_set( args.url.username, args.url.password )
    mqttc.on_connect = on_mqtt_connect
    mqttc.connect( args.url.hostname, args.url.port if args.url.port!=None else 1883, 60 )
    mqttc.loop_start()

    def parse_log_line( line ):
        logging.debug( line )

        sensor_state = None
        match = args.on.match( line )
        if match is not None:
           sensor_state = 1
        else:
           match = args.off.match( line )
           if match is not None:
              sensor_state = 0

        if match is not None:
           sensor = match.group('sensor')
           if sensor not in sensors_dict or sensors_dict[sensor] != sensor_state:
               sensors_dict[sensor] = sensor_state
               logging.info("Sensor %s changed state to %d" % (sensor, sensor_state) )
               mqttc.publish( args.prefix+sensor, sensor_state )
           pass

    f = open(args.input ,"r")
    if args.all:
        for line in f.readlines():
            parse_log_line(line.strip())
    f.read()

    watcher = inotify.adapters.Inotify()
    watcher.add_watch( args.input, mask = inotify.constants.IN_MODIFY | inotify.constants.IN_CREATE )

    for event in watcher.event_gen(yield_nones=False):
        (_, type_names, path, filename) = event
        if 'IN_CREATE' in type_names:
            f = open(args.input, "r")

        if 'IN_MODIFY' in type_names:
            changed_data = f.read()
            for line in changed_data.strip().split("\n"):
                parse_log_line( line.strip() )
    pass

if __name__=="__main__":
    main()
