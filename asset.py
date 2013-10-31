from pulp import *
import urllib

prob = LpProblem("Assets", LpMinimize)

allocation = { 'stock_us'   : 0.36,
               'stock_intl' : 0.36,
               'reit'       : 0.064,
               'bond'       : 0.2 }

account_value = { '401k'     : 100000,
                  'ira'      : 10000,
                  'personal' : 100000 }
v_total = sum(account_value.values())

ideal_value = {}
for asset_class in allocation.keys():
    ideal_value[asset_class] = allocation[asset_class] * v_total

assets = {'401k' : [ 'VEMPX', 'VTPSX', 'VGSNX', 'VIIIX', 'VBMPX'  ],
          'ira' : [ 'VTIAX', 'VTSAX', 'VGSLX', 'VFSVX', 'VSIAX' ],
          'personal' : [ 'VTSAX', 'VFWAX' ] }

funds = { 'VEMPX' : { 'er' : 0.1,
                      'composition' :
                          { 'stock_us'   : 1,
                            'stock_intl' : 0,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VTPSX' : { 'er' : 0.1,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 1,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VGSNX' : { 'er' : 0.08,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 0,
                            'reit'       : 1,
                            'bonds'      : 0 } },
          'VIIIX' : { 'er' : 0.02,
                      'composition' :
                          { 'stock_us'   : 1,
                            'stock_intl' : 0,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VBMPX' : { 'er' : 0.05,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 0,
                            'reit'       : 0,
                            'bonds'      : 1 } },
          'VTIAX' : { 'er' : 0.16,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 1,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VTSAX' : { 'er' : 0.05,
                      'composition' :
                          { 'stock_us'   : 1,
                            'stock_intl' : 0,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VGSLX' : { 'er' : 0.1,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 0,
                            'reit'       : 1,
                            'bonds'      : 0 } },
          'VFSVX' : { 'er' : 0.45,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 1,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VSIAX' : { 'er' : 0.1,
                      'composition' :
                          { 'stock_us'   : 1,
                            'stock_intl' : 0,
                            'reit'       : 0,
                            'bonds'      : 0 } },
          'VFWAX' : { 'er' : 0.15,
                      'composition' :
                          { 'stock_us'   : 0,
                            'stock_intl' : 1,
                            'reit'       : 0,
                            'bonds'      : 0 } } }

# Lookup current prices
for fund in funds.keys():
    params = urllib.urlencode({ 's' : fund, 'f' : 'l1', 'e' : '.csv' })
    f = urllib.urlopen("http://download.finance.yahoo.com/d/quotes.csv", params)
    funds[fund]['price'] = float(f.read())

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

# Ensure US stock allocation
prob += (funds['VEMPX']['price'] * shares['401k']['VEMPX'] +
         funds['VIIIX']['price'] * shares['401k']['VIIIX'] +
         funds['VTSAX']['price'] * shares['ira']['VTSAX'] +
         funds['VTSAX']['price'] * shares['personal']['VTSAX'] ==
         ideal_value['stock_us'])

# Ensure Int'l stock allocation
prob += (funds['VTPSX']['price'] * shares['401k']['VTPSX'] +
         funds['VTIAX']['price'] * shares['ira']['VTIAX'] +
         funds['VFWAX']['price'] * shares['personal']['VFWAX'] ==
         ideal_value['stock_intl'])

# Ensure REIT allocation
prob += (funds['VGSNX']['price'] * shares['401k']['VGSNX'] +
         funds['VGSLX']['price'] * shares['ira']['VGSLX'] ==
         ideal_value['reit'])

# Ensure US Bond allocation
prob += (funds['VBMPX']['price'] * shares['401k']['VBMPX'] ==
         ideal_value['bond'])

# Admiral minima + 10%
prob += (funds['VTSAX']['price'] * shares['ira']['VTSAX'] >= 11000)
prob += (funds['VSIAX']['price'] * shares['ira']['VSIAX'] >= 11000)
prob += (funds['VGSLX']['price'] * shares['ira']['VGSLX'] >= 11000)
prob += (funds['VFWAX']['price'] * shares['personal']['VFWAX'] >= 11000)

prob.solve()

print "Status: ", LpStatus[prob.status]

for v in prob.variables():
    print v.name, "=", v.varValue

print "Total cost", value(prob.objective)/v_total
