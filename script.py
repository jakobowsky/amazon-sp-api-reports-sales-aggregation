import csv
import json
import time

import pandas as pd
import requests
import seaborn as sns
from sp_api.api import Reports, Sales
from sp_api.base import Marketplaces, ReportType, ProcessingStatus, Granularity

from keys import CLIENT_CONFIG

if __name__ == '__main__':
    report_type = ReportType.GET_FBA_MYI_ALL_INVENTORY_DATA
    res = Reports(credentials=CLIENT_CONFIG, marketplace=Marketplaces.US)
    data = res.create_report(reportType=report_type)
    report = data.payload
    print(report)
    report_id = report['reportId']

    res = Reports(credentials=CLIENT_CONFIG, marketplace=Marketplaces.US)
    data = res.get_report(report_id)

    report_data = ''

    while data.payload.get('processingStatus') not in [ProcessingStatus.DONE, ProcessingStatus.FATAL,
                                                       ProcessingStatus.CANCELLED]:
        print(data.payload)
        print('Sleeping...')
        time.sleep(2)
        data = res.get_report(report_id)

    if data.payload.get('processingStatus') in [ProcessingStatus.FATAL, ProcessingStatus.CANCELLED]:
        print("Report failed!")
        report_data = data.payload
    else:
        print("Success:")
        print(data.payload)
        report_data = res.get_report_document(data.payload['reportDocumentId'])
        print("Document:")
        print(report_data.payload)

    report_url = report_data.payload.get('url')
    print(report_url)

    res = requests.get(report_url)
    decoded_content = res.content.decode('cp1252')
    reader = csv.DictReader(decoded_content.splitlines(), delimiter='\t')

    data_list = []
    for row in reader:
        data = {
            'sku': row['sku'],
            'fnsku': row['fnsku'],
            'asin': row['asin'],
            'product_name': row['product-name'],
            'condition': row['condition'],
            'your_price': int(float(row['your-price'] or '0') * 100),
            'mfn_listing_exists': row['mfn-listing-exists'] == 'Yes',
            'mfn_fulfillable_quantity': row['mfn-fulfillable-quantity'] or None,
            'afn_listing_exists': row['afn-listing-exists'] == 'Yes',
            'afn_warehouse_quantity': row['afn-warehouse-quantity'],
            'afn_fulfillable_quantity': row['afn-fulfillable-quantity'],
            'afn_unsellable_quantity': row['afn-unsellable-quantity'],
            'afn_reserved_quantity': row['afn-reserved-quantity'],
            'afn_total_quantity': row['afn-total-quantity'],
            'afn_inbound_working_quantity': row['afn-inbound-working-quantity'],
            'afn_inbound_shipped_quantity': row['afn-inbound-shipped-quantity'],
            'afn_inbound_receiving_quantity': row['afn-inbound-receiving-quantity'],
            'afn_researching_quantity': row['afn-researching-quantity'],
            'afn_reserved_future_supply': row['afn-reserved-future-supply'],
            'afn_future_supply_buyable': row['afn-future-supply-buyable'],
            'per_unit_volume': float(row['per-unit-volume']) if row['per-unit-volume'] else None,
        }
        data_list.append(data)
    print(data_list)
    with open('./responses/data.json', 'w') as out:
        json.dump(data_list, out)

    f = open('./responses/data.json')
    data = json.load(f)
    asins = [x['asin'] for x in data][:5]

    marketplaces = dict(US=Marketplaces.US, CA=Marketplaces.CA)
    data = []
    for asin in asins:
        for country, marketplace_id in marketplaces.items():
            sales = Sales(credentials=CLIENT_CONFIG, marketplace=marketplace_id)
            res = sales.get_order_metrics(interval=('2021-09-01T00:00:00-07:00', '2022-09-28T00:00:00-07:00'),
                                          granularity=Granularity.TOTAL, asin=asin)
            metrics = res.payload[0]
            data.append({'unit_count': metrics['unitCount'], 'order_item_count': metrics['orderItemCount'],
                         'order_count': metrics['orderCount'], 'country': country, 'asin': asin})

    df = pd.DataFrame(data)
    print(df)

    sns.set_theme(style='whitegrid')
    g = sns.catplot(
        data=df, kind="bar",
        x="asin", y="unit_count", hue="country",
        errorbar="sd", palette="dark", alpha=.6, height=6
    )
    g.despine(left=True)
    g.set_axis_labels("", "Unit count")
    g.legend.set_title("")
