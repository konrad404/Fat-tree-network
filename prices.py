class Prices:
    rj45_cat_7 = 579 / 100
    rack_42u = 2000
    dell_poweredge_r450_xs = 19399

    @staticmethod
    def getRackPriceBasedOnHeight(rack_height):
        return Prices.rack_42u * rack_height / 42
