import json
import pandas as pd
from datetime import datetime
import mstarpy
import numpy as np
from numpy_financial import irr

# Load the JSON data
def load_data(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Calculate units and perform FIFO
def calculate_units(transactions):
    units = {}
    
    for trxn in transactions:
        folio = trxn['folio']
        isin = trxn['isin']
        units_key = (folio, isin)
        
        if units_key not in units:
            units[units_key] = {'total_units': 0, 'transactions': []}
        
        trxn_units = float(trxn['trxnUnits'])
        trxn_price = float(trxn['purchasePrice'])
        
        if trxn_units > 0:  # Buy
            units[units_key]['transactions'].append({'units': trxn_units, 'price': trxn_price})
            units[units_key]['total_units'] += trxn_units
        else:  # Sell
            units_to_sell = abs(trxn_units)
            while units_to_sell > 0 and units[units_key]['transactions']:
                first_buy = units[units_key]['transactions'][0]
                if first_buy['units'] > units_to_sell:
                    first_buy['units'] -= units_to_sell
                    units[units_key]['total_units'] -= units_to_sell
                    units_to_sell = 0
                else:
                    units_to_sell -= first_buy['units']
                    units[units_key]['total_units'] -= first_buy['units']
                    units[units_key]['transactions'].pop(0)

    return units

# Calculate portfolio value and gain
def calculate_portfolio(units, current_navs):
    total_value = 0
    total_gain = 0
    portfolio_details = {}
    
    for (folio, isin), data in units.items():
        remaining_units = data['total_units']
        current_nav = current_navs.get(isin, 0)
        current_value = remaining_units * current_nav
        
        # Calculate acquisition cost
        acquisition_cost = sum(trxn['units'] * trxn['price'] for trxn in data['transactions'])
        
        gain = current_value - acquisition_cost
        
        total_value += current_value
        total_gain += gain
        
        portfolio_details[isin] = {
            'remaining_units': remaining_units,
            'current_value': current_value,
            'gain': gain
        }

    return total_value, total_gain, portfolio_details

# Fetch current NAVs
def fetch_current_navs(isins):
    current_navs = {}
    for isin in isins:
        fund = mstarpy.Funds(term=isin, country="in")
        end_date = datetime.now()
        start_date = end_date - pd.DateOffset(days=365)
        history = fund.nav(start_date=start_date, end_date=end_date, frequency="daily")
        current_navs[isin] = history['nav'].iloc[-1]  # Get the latest NAV
    return current_navs

# Calculate XIRR
def calculate_xirr(transactions):
    cash_flows = []
    dates = []
    
    for trxn in transactions:
        trxn_date = datetime.strptime(trxn['trxnDate'], "%d-%b-%Y")
        trxn_amount = float(trxn['trxnAmount'])
        
        cash_flows.append(trxn_amount)
        dates.append(trxn_date)

    # Add the current portfolio value as the final cash flow
    current_value = sum(cash_flows)  # This is a placeholder; replace with actual current value
    cash_flows.append(current_value)
    dates.append(datetime.now())

    # Calculate XIRR
    xirr_value = irr(np.array(cash_flows)) * 100  # Convert to percentage
    return xirr_value

# Main function
def main(file_path):
    data = load_data(file_path)
    transactions = data['data'][0]['dtSummary']  # Adjust based on actual structure
    units = calculate_units(transactions)
    
    # Fetch current NAVs for all unique ISINs
    isins = {trxn['isin'] for trxn in transactions}
    current_navs = fetch_current_navs(isins)
    
    total_value, total_gain, portfolio_details = calculate_portfolio(units, current_navs)
    
    print(f"Total Portfolio Value: {total_value:.2f}")
    print(f"Total Portfolio Gain: {total_gain:.2f}")
    print("Portfolio Details:")
    for isin, details in portfolio_details.items():
        print(f"ISIN: {isin}, Remaining Units: {details['remaining_units']}, Current Value: {details['current_value']:.2f}, Gain: {details['gain']:.2f}")

    # Calculate XIRR if needed
    xirr_value = calculate_xirr(transactions)
    print(f"Portfolio XIRR: {xirr_value:.2f}%")

# Run the main function
if name == "main":
    main('portfolio_data.json')  # Update the path to your JSON file