from pulp import *
from lxml import etree
import requests

prob = LpProblem("Assets", LpMinimize)

allocation = { 'stock_us'   : 0.8 * 0.9 * 0.6,
               'stock_intl' : 0.8 * 0.9 * 0.4,
               'reit'       : 0.8 * 0.1,
               'bond_us'    : 0.2 * 0.8,
               'bond_intl'  : 0.2 * 0.2 }

category = { 'Mid-Cap Blend' : { 'stock_us' : 1 },
             'Foreign Large Blend' : { 'stock_intl' : 1 },
             'Real Estate' : { 'reit' : 1 },
             'Large Blend' : { 'stock_us' : 1 },
             'Intermediate-Term Bond' : { 'bond_us' : 1 },
             'Foreign Small/Mid Blend' : { 'stock_intl' : 1 },
             'Small Value' : { 'stock_us' : 1 },
             'World Bond' : { 'bond_intl' : 1 }
             }

assets = {'401k' : { 'VEMPX' : 1000,
                     'VTPSX' : 1000,
                     'VGSNX' : 1000,
                     'VIIIX' : 1000,
                     'VBMPX' : 1000 },
          'ira' : { 'VTIAX' : 1000,
                    'VTSAX' : 1000,
                    'VGSLX' : 1000,
                    'VTABX' : 1000 },
          'personal' : { 'VTSAX' : 1000,
                         'VFWAX' : 1000 } }

funds = {}
for accounts in assets.keys():
    for fund in assets[accounts].keys():
        funds[fund] = {}

# Lookup current prices
for fund in funds.keys():
    params = { 't' : 'XNAS:' + fund, 'region' : 'usa', 'culture' : 'en-US',
               'cur' : 'USD'}
    r = requests.get('http://quotes.morningstar.com/fund/c-header',
                     params=params)
    tree = etree.fromstring(r.text, etree.HTMLParser())
    funds[fund]['price'] = float(tree.xpath(
            "//span[@vkey='NAV']/text()")[0].strip())
    funds[fund]['er'] = float(tree.xpath(
            "//span[@vkey='ExpenseRatio']/text()")[0].strip().rstrip('%'))
    composition = category[tree.xpath(
            "//span[@vkey='MorningstarCategory']/text()")[0].strip()]
    funds[fund]['composition'] = composition
    print fund, '@', funds[fund]['price'], funds[fund]['er']

account_value = {}
for account in assets.keys():
    account_value[account] = sum([ shares * funds[fund]['price']
                                   for (fund, shares)
                                   in assets[account].items() ])
    print '%s value: %0.2f' % (account, account_value[account])
v_total = sum(account_value.values())

ideal_value = {}
for asset_class in allocation.keys():
    ideal_value[asset_class] = allocation[asset_class] * v_total

shares = {}

for account in assets.keys():
    shares[account] = {}
    for fund in assets[account]:
        shares[account][fund] = LpVariable(account + ':' + fund, 0, None)

# Minimize average expense ratio
prob += (sum([funds[x]['er'] * funds[x]['price'] * shares['401k'][x] for x in
              shares['401k'].keys()]) +
         sum([funds[x]['er'] * funds[x]['price'] * shares['ira'][x] for x in
              shares['ira'].keys()]) +
         sum([funds[x]['er'] * funds[x]['price'] * shares['personal'][x] for x in
              shares['personal'].keys()]))

# Total account values are fixed
for account in account_value.keys():
    prob += (sum([funds[x]['price'] * shares[account][x] for x in
                  shares[account].keys()]) == account_value[account])

# Use VIIIX and VEMPX to approximate total market
prob += (0.18 * funds['VIIIX']['price'] * shares['401k']['VIIIX'] -
         0.82 * funds['VEMPX']['price'] * shares['401k']['VEMPX'] == 0)

# Set up the asset allocation constraints for a given account and asset class
def asset_class_allocation_constraints(account, asset_class):
    return sum([funds[fund]['composition'][asset_class] *
                funds[fund]['price'] *
                shares[account][fund] for fund in shares[account].keys()
                if asset_class in funds[fund]['composition']])

# Ensure individual asset allocations
for asset_class in allocation.keys():
    prob += (sum([ 
                asset_class_allocation_constraints(account, asset_class)
                for account in assets.keys() ]) ==
             ideal_value[asset_class])

# Admiral minima + 10%
prob += (funds['VTSAX']['price'] * shares['ira']['VTSAX'] >= 11000)
prob += (funds['VGSLX']['price'] * shares['ira']['VGSLX'] >= 11000)
prob += (funds['VFWAX']['price'] * shares['personal']['VFWAX'] >= 11000)

prob.solve()

print "Status: ", LpStatus[prob.status]

for v in prob.variables():
    print "%s: %f ($%0.2f)" % (v.name, v.varValue, funds[v.name.split(':')[1]]['price'] * v.varValue)

print "Total cost", value(prob.objective)/v_total
