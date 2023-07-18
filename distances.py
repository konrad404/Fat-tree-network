import json, sys

class Distances:
    core_to_aggregation = 100
    core_to_edge = 150
    aggregation_to_edge = 20
    edge_to_host = 10

def loadDistances():
    with open('distances.json') as json_file:
        data = json.load(json_file)
        for key in data:
            setattr(Distances, key, data[key])

loadDistances()