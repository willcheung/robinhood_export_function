from csv import writer
from datetime import date
from pathlib import Path
import robin_stocks.helper as helper
import robin_stocks.orders as orders
import robin_stocks.stocks as stocks

@helper.login_required
def export_completed_stock_orders():
    """Write all completed orders to a csv file

    :param dir_path: Absolute or relative path to the directory the file will be written.
    :type dir_path: str
    :param file_name: An optional argument for the name of the file. If not defined, filename will be stock_orders_{current date}
    :type file_name: Optional[str]

    """
    all_orders = orders.get_all_stock_orders()
    data = []
    data.append([
        'symbol',
        'date',
        'order_type',
        'side',
        'fees',
        'quantity',
        'average_price'
    ])
    for order in all_orders:
        if order['state'] == 'filled' and order['cancel'] is None:
            data.append([
                stocks.get_symbol_by_url(order['instrument']),
                order['last_transaction_at'],
                order['type'],
                order['side'],
                order['fees'],
                order['quantity'],
                order['average_price']
            ])
    
    return data


@helper.login_required
def export_completed_option_orders():
    """Write all completed option orders to a csv

        :param dir_path: Absolute or relative path to the directory the file will be written.
        :type dir_path: str
        :param file_name: An optional argument for the name of the file. If not defined, filename will be option_orders_{current date}
        :type file_name: Optional[str]

    """
    all_orders = orders.get_all_option_orders()
    data = []
    data.append([
        'chain_symbol',
        'expiration_date',
        'strike_price',
        'option_type',
        'side',
        'order_created_at',
        'direction',
        'order_quantity',
        'order_type',
        'opening_strategy',
        'closing_strategy',
        'price',
        'processed_quantity'
    ])
    for order in all_orders:
        if order['state'] == 'filled':
            for leg in order['legs']:
                instrument_data = helper.request_get(leg['option'])
                data.append([
                    order['chain_symbol'],
                    instrument_data['expiration_date'],
                    instrument_data['strike_price'],
                    instrument_data['type'],
                    leg['side'],
                    order['created_at'],
                    order['direction'],
                    order['quantity'],
                    order['type'],
                    order['opening_strategy'],
                    order['closing_strategy'],
                    order['price'],
                    order['processed_quantity']
                ])
    
    return data
