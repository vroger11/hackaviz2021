import argparse
import json

import pandas as pd
import numpy as np
from os.path import join
from bokeh.plotting import figure, save, output_file
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar
from bokeh.tile_providers import CARTODBPOSITRON, get_provider


FR_TOOLTIPS = [
    ('Nom de la commune', '@commune_name'),
    ('Nombre de transactions', '@transaction_number'),
    ("Nombre de transactions de maisons", "@house_number"),
    ("Nombre de transactions de locaux industriels, commerciaux ou assimilés", "@indus_number"),
    ("Nombre de transactions d'appartements", "@app_number"),
    ("Valeur moyenne des transactions", "@mean_value")
]

FR_TITLE = "Transactions foncières en Occitanie du 1er janvier 2016 au 31 décembre 2020."

EN_TOOLTIPS = [
    ('Name of the municipality', '@commune_name'),
    ('Number of transactions', '@transaction_number'),
    ("Number of home transactions", "@house_number"),
    ("Number of transactions of industrial, commercial or similar premises", "@indus_number"),
    ("Nombre de transactions appartement", "@app_number"),
    ("Number of apartment transactions", "@mean_value")
]

EN_TITLE = "Land transactions in Occitania from January 1st 2016 to December 31st 2020."

def make_figures(data_folderpath, language, result_name):
    """
    Parameters
    ----------
    data_folderpath: str
        Path where the hackaviz 2021 data is located.
    language: str
        One of the following: 'French' or 'English'
    """
    # load data
    qp_df = pd.read_csv(join(data_folderpath, "qp.csv"))
    foncier_qp_df = pd.read_csv(join(data_folderpath, "foncier_qp.csv"))
    with open(join(data_folderpath, "communes.geojson"), 'r') as geojson_file:
        data = json.load(geojson_file)

    # compute some informations
    max_transaction = 0
    for i in range(len(data['features'])):
        transaction_number = len(foncier_qp_df[foncier_qp_df["nom_commune"] == data['features'][i]["properties"]["nom_commune"]])
        max_transaction = transaction_number if transaction_number > max_transaction else max_transaction
        data['features'][i]["properties"]['transaction_number'] = transaction_number
        data['features'][i]["properties"]['house_number'] = len(foncier_qp_df[(foncier_qp_df["nom_commune"] == data['features'][i]["properties"]["nom_commune"]) & (foncier_qp_df["type_local"] == "Maison")])
        data['features'][i]["properties"]['indus_number'] = len(foncier_qp_df[(foncier_qp_df["nom_commune"] == data['features'][i]["properties"]["nom_commune"]) & (foncier_qp_df["type_local"] == "Local industriel. commercial ou assimilé")])
        data['features'][i]["properties"]['app_number'] = len(foncier_qp_df[(foncier_qp_df["nom_commune"] == data['features'][i]["properties"]["nom_commune"]) & (foncier_qp_df["type_local"] == "Appartement")])

        # round value and deal nans when there is no transactions
        valeur = foncier_qp_df[foncier_qp_df["nom_commune"] == data['features'][i]["properties"]["nom_commune"]]["valeur_fonciere"].mean(skipna=True)
        valeur = valeur if not np.isnan(valeur) else 0
        data['features'][i]["properties"]['mean_value'] = f"{round(valeur)}€"

        # change wgs84 into mercator
        for coordinate in data['features'][i]['geometry']['coordinates'][0][0]:
            k = 6378137
            coordinate[0] = coordinate[0] * (k * np.pi/180.0)
            coordinate[1] = np.log(np.tan((90 + coordinate[1]) * np.pi/360.0)) * k

    geo_source = GeoJSONDataSource(geojson=json.dumps(data))

    if language == "English":
        title = EN_TITLE
        tooltips = EN_TOOLTIPS
    elif language  == "French":
        title = FR_TITLE
        tooltips = FR_TOOLTIPS
    else:
        raise ValueError(f"{language} language not supported.")

    p = figure(title=title,
               tooltips=tooltips, width=550, height=500,
               x_axis_type="mercator", y_axis_type="mercator",
               x_range=(-40000, 640000), y_range=(5300000, 5500000))

    tile_provider = get_provider(CARTODBPOSITRON)
    p.add_tile(tile_provider)

    color_mapper = LinearColorMapper(palette="YlOrRd9", low=0, high=max_transaction)

    p.patches('xs', 'ys', fill_alpha=0.5, fill_color={'field': 'transaction_number', 'transform': color_mapper},
              line_color='black', line_width=0.7, source=geo_source)

    color_bar = ColorBar(color_mapper=color_mapper,label_standoff=12, border_line_color=None, location=(0,0))

    p.add_layout(color_bar, 'right')
    p.toolbar.active_scroll = "auto"

    output_file(f"{result_name}.html")
    save(p)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Produce the figure Vincent ROGER used for his hackaviz participation.')
    parser.add_argument("--data_folderpath", type=str,
                         help="Path where the hackaviz 2021 data is located.")
    parser.add_argument("--language", type=str, default="French",
                         help="The language for the figure, can be 'French' or 'Encglish'.")
    parser.add_argument("--fn_figure", type=str, default="commune_transactions_heatmap",
                         help="Filename of the outputed figure.")

    args = parser.parse_args()
    make_figures(args.data_folderpath, args.language, args.fn_figure)