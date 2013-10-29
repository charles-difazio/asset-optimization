from pulp import *
import urllib

prob = LpProblem("Assets", LpMinimize)

c_stockus = 0.36
c_stockintl = 0.36
c_reit = 0.064
c_bond = 0.2

v_401k = 100000
v_ira = 10000
v_personal = 100000
v_total = v_401k + v_ira + v_personal

v_stockus = c_stockus * v_total
v_stockintl = c_stockintl * v_total
v_reit = c_reit * v_total
v_bond = c_bond * v_total

assets = {'401k' : [ 'VEMPX', 'VTPSX', 'VGSNX', 'VIIIX', 'VBMPX'  ],
          'ira' : [ 'VTIAX', 'VTSAX', 'VGSLX', 'VFSVX', 'VSIAX' ],
          'personal' : [ 'VTSAX', 'VFWAX' ] }

funds = { 'VEMPX' : { 'er' : 0.1,
                      'composition' : [1,0,0,0] },
          'VTPSX' : { 'er' : 0.1,
                      'composition' : [0,1,0,0] },
          'VGSNX' : { 'er' : 0.08,
                      'composition' : [0,0,1,0] },
          'VIIIX' : { 'er' : 0.02,
                      'composition' : [1,0,0,0] },
          'VBMPX' : { 'er' : 0.05,
                      'composition' : [0,0,0,1] },
          'VTIAX' : { 'er' : 0.16,
                      'composition' : [0,1,0,0] },
          'VTSAX' : { 'er' : 0.05,
                      'composition' : [1,0,0,0] },
          'VGSLX' : { 'er' : 0.1,
                      'composition' : [0,0,1,0] },
          'VFSVX' : { 'er' : 0.45,
                      'composition' : [0,1,0,0] },
          'VSIAX' : { 'er' : 0.1,
                      'composition' : [1,0,0,0] },
          'VFWAX' : { 'er' : 0.15,
                      'composition' : [0,1,0,0] } }

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

# Total 401k value is fixed
prob += (sum([funds[x]['price'] * shares['401k'][x] for x in
              shares['401k'].keys()]) == v_401k)

# Total IRA value is fixed
prob += (sum([funds[x]['price'] * shares['ira'][x] for x in 
              shares['ira'].keys()]) == v_ira)

# Total personal value is fixed
prob += (sum([funds[x]['price'] * shares['personal'][x] for x in
              shares['personal'].keys()]) == v_personal)

# Use VIIIX and VEMPX to approximate total market
prob += (0.18 * funds['VIIIX']['price'] * shares['401k']['VIIIX'] -
         0.82 * funds['VEMPX']['price'] * shares['401k']['VEMPX'] == 0)

# Ensure US stock allocation
prob += (funds['VEMPX']['price'] * shares['401k']['VEMPX'] +
         funds['VIIIX']['price'] * shares['401k']['VIIIX'] +
         funds['VTSAX']['price'] * shares['ira']['VTSAX'] +
         funds['VTSAX']['price'] * shares['personal']['VTSAX'] == v_stockus)

# Ensure Int'l stock allocation
prob += (funds['VTPSX']['price'] * shares['401k']['VTPSX'] +
         funds['VTIAX']['price'] * shares['ira']['VTIAX'] +
         funds['VFWAX']['price'] * shares['personal']['VFWAX'] == v_stockintl)

# Ensure REIT allocation
prob += (funds['VGSNX']['price'] * shares['401k']['VGSNX'] +
         funds['VGSLX']['price'] * shares['ira']['VGSLX'] == v_reit)

# Ensure US Bond allocation
prob += (funds['VBMPX']['price'] * shares['401k']['VBMPX'] == v_bond)

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
