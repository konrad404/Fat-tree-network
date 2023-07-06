import json

class Prices:
    rj45_cat_7 = 579 / 100
    rack_42u = 2000
    dell_poweredge_r450_xs = 19399
    router_price = 6348.66
    switch_price = 6476.75

    @staticmethod
    def getRackPriceBasedOnHeight(rack_height):
        return Prices.rack_42u * rack_height / 42

def loadPrices():
    with open('prices.json') as json_file:
        data = json.load(json_file)
        for key in data:
            setattr(Prices, key, data[key])

loadPrices()
