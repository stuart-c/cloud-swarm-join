# cloud-swarm-join
A Docker image to automatically join a Docker Swarm. Designed to be used as part of the startup of a new Docker server for public & private clouds.

## Usage
    docker run --rm --net=host --env DISCOVERY_BACKEND="consul://consul.example.com:8500/" --volume /var/run/docker.sock:/var/run/docker.sock stuartc/cloud-swarm-join

This will advertise the default IP of the host to the Docker Swarm that can be found at the **consul.example.com:8500** Consul server.

This container is designed to be started automatically as the host boots. One example is to use the cloud-init system for operating systems such as RancherOS:

    rancher:
      services:
        cloud-swarm-join:
          image: stuartc/cloud-swarm-join
          environment:
            - "CONTAINER_NAME=swarm"
            - "DISCOVERY_BACKEND=consul://consul.example.com:8500/{{ Prefix }}"
            - "AWS_REGION=eu-west-1"
          volumes:
            - /var/run/docker.sock:/var/run/docker.sock

## Using with Amazon EC2
There is also built in support for Amazon EC2. The internal IP address of the EC2 instance will be automatically looked up using an instance metadata lookup, so using host networking isn't required.

Additionally instance tags can be used to set some or all of the image options as well as for additional substitution variables.

### Substitution Variables
Moustache style substitution tags (e.g. `{{ Variable }}`) can be used with all instance tags being available. Additionally those instance tags can be overridden via container environment variables (all upper-case equivalent of the tag name).

## Configuration Settings
These can be set via EC2 instance tags (mixed case) or container environment variables (all upper-case).

**ContainerName** or **CONTAINER_NAME**
The name to use for the Swarm node agent command container. Defaults to using an auto-generated name.

**DiscoveryBackend** or **DISCOVERY_BACKEND**
The Swarm discovery backend details to use. Defaults to `token://{{ Token }}` which is not recommended for production use, but if used would expect either an instance tag called `Token` or a container environment variable called `TOKEN` to be set to the Swarm token.

**DockerApiVersion** or **DOCKER_API_VERSION**
The Docker API version to use when connecting to the Docker daemon to start the Swarm agent container. Defaults to auto-detect.

**DockerHost** or **DOCKER_HOST**
The Docker host to use when starting the Swarm agent container. Defaults to the Docker socket at `/var/run/docker.sock` which would need to be host volume mounted.

**IpAddress** or **IP_ADDRESS**
Allows the IP address to advertise to Swarm to be set. Normally this wouldn't be used, with the IP address instead being detected via an instance metadata lookup (for Amazon EC2) or the default IP (you will need to set host networking for the container for that to work).

**Options** or **SWARM_OPTIONS**
Additional options for passing to the Swarm join command, for example to set TTL settings.

The following are only available as container environment variables:

**SKIP_METADATA**
If set to something true (y, yes, t, true, on or 1) don't try to find the host's IP address or instance tags via a metadata lookup. May speed things up slightly for non-EC2 hosts.

**AWS_REGION**
**AWS_ACCESS_KEY_ID**
**AWS_SECRET_ACCESS_KEY**
The Amazon EC2 region & security details. If the access and secret keys aren't set an instance IAM profile can also be used. If the region isn't set it defaults to eu-west-1.

