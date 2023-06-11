# Fat tree network analysis

### Intro
The project is to create and analyze the fat tree network topology. It will consist of following steps:
1. Creation of the large-scale fat tree network topology model using NetBox simulation tool.
2. Performing cost and scalability analysis for fat tree networks including physical placement considerations.
3. Adding automation to the project simulations.

### Fat tree topology
Fat Tree topology is a popular and scalable network architecture commonly used in data center networks. It consists of multiple layers of switches, arranged in a hierarchical manner, with increasing levels of connectivity as you move up the hierarchy. This architecture provides a high degree of fault tolerance, bandwidth capacity, and scalability, making it an ideal choice for large-scale data centers.

| *Fat tree topology scheme example* |
|:--:| 
| ![image](https://user-images.githubusercontent.com/72918433/236562694-c67308b1-7d7f-4dfc-b243-9119a1dcc5c5.png) | 


### NetBox
NetBox is a versatile open-source network management and automation tool that allows to efficiently manage network infrastructures. With NetBox, users can easily model network topologies, manage IP addresses, and automate routine network management tasks. It's intuitive web interface and REST API make it easy to integrate with other tools and systems.

### Setup
**NetBox**<br />
Take the following steps to run a local NetBox server via Docker:
* Ensure that your Docker daemon is running.
* Run the ```netbox/setup.sh``` script
* Once all containers are up and running, execute the following commands:
  * ```cd netbox-docker```
  * ```docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser```
  * Remember credentials you provide, paste them into the ```credentials.json```
* Open http://localhost:8000/ to verify if everything was set up correctly.