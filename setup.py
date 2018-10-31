#!/usr/bin/python
import setuptools

                     

setuptools.setup(
    name="mqtt_services",
    version="0.0.1",
    author="Alexey Ponimash",
    author_email="alexey.ponimash@gmail.com",
    description="MQTT Services",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/led-spb",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
       'requests>=2.10.0',
       'inotify', 
       'paho_mqtt', 
       'RPi.GPIO',
       'jinja2',
       'influxdb'
    ],
    entry_points={
       'console_scripts': [
            'json2mqtt = mqtt_services.json2mqtt:main',
            'mqtt2carbon = mqtt_services.mqtt2carbon:main',
            'mqtt2influx = mqtt_services.mqtt2influx:main',
            'gpiosensors = mqtt_services.gpiosensors:main',
            'logsensors = mqtt_services.logsensors:main',
       ]
    },
)
