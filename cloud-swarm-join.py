#!/bin/env python

import os
import boto3
import socket
import pystache
import requests

from docker import Client
from distutils.util import strtobool
from requests.exceptions import ConnectionError

def get_metadata(item):
    # Skip all metadata service calls if environment variable set to true
    if strtobool(os.environ.get('SKIP_METADATA', 'no')):
        return

    try:
        response = requests.get('http://169.254.169.254/latest/meta-data/' + item)
    except ConnectionError:
        return

    if response.status_code != 200:
        return

    return response.text

def get_ip_address():
    ip_address = get_metadata('local-ipv4')

    # If not running under EC2
    if not ip_address:
        # connecting to a UDP address doesn't send packets
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 53))
        ip_address = sock.getsockname()[0]

    return ip_address

def get_ec2_instance_tags():
    # Lookup instance ID from metadata service
    instance_id = get_metadata('instance-id')

    # If not running under EC2
    if not instance_id:
        return {}

    ec2 = boto3.resource('ec2', region_name=os.environ.get('AWS_REGION'))

    instance = ec2.Instance(instance_id)

    return {x['Key']: x['Value'] for x in instance.tags}

def render(template, data):
    # Loop until all template tags are resolved
    while '{{' in template:
        template = pystache.render(template, data)

    return template

def override_tags(data):
    aliases = {
        'ContainerName': 'CONTAINER_NAME',
        'DiscoveryBackend': 'DISCOVERY_BACKEND',
        'DockerApiVersion': 'DOCKER_API_VERSION',
        'DockerHost': 'DOCKER_HOST',
        'IpAddress': 'IP_ADDRESS',
        'Options': 'SWARM_OPTIONS',
    }

    defaults = {
        'ContainerName': None,
        'DiscoveryBackend': 'token://{{ Token }}',
        'DockerApiVersion': 'auto',
        'DockerHost': 'unix://var/run/docker.sock',
        'Port': 2375,
    }

    # Ensure some keys exist
    for key in aliases:
        if key not in data:
            data[key] = ''

    # Override from environment variables
    for key in data:
        if key.upper() in os.environ:
            data[key] = os.environ.get(key.upper())

    # Some nicer environment variable aliases
    for key in aliases:
        if aliases[key] in os.environ:
            data[key] = os.environ.get(aliases[key])

    # Set some defaults
    for key in defaults:
        if key not in data or not data[key]:
            data[key] = defaults[key]

    return data

def main():
    # Fetch EC2 instance tags
    tags = get_ec2_instance_tags()

    # Set IpAddress tag to instance IP address
    tags['IpAddress'] = get_ip_address()

    # Override tags using environment variables
    tags = override_tags(tags)

    # Docker Swarm join command
    commands = [
        'join',
        '--advertise={{ IpAddress }}:{{ Port }}',
        '{{ Options }}',
        '{{ DiscoveryBackend }}'
    ]

    commands = [render(x, tags) for x in commands]

    # Docker settings
    docker_api_version = render(tags.get('DockerApiVersion'), tags)
    docker_host = render(tags.get('DockerHost'), tags)

    # Default of None will cause container name to be auto-generated
    container_name = tags.get('ContainerName')

    # Start Swarm container
    cli = Client(base_url=docker_host, version=docker_api_version)

    cli.pull('swarm', tag='latest')

    container = cli.create_container(
        image='swarm',
        name=container_name,
        command=[x for x in commands if x]
    )

    cli.start(container=container.get('Id'))

if __name__ == "__main__":
    main()
