from Robinhood import Robinhood
import getpass
import collections
import argparse
import ast
import os

logged_in = False

# hard code your credentials here to avoid entering them each time you run the script
username = ""
password = ""

parser = argparse.ArgumentParser(description='Export Robinhood trades to a CSV file')
parser.add_argument('--debug', action='store_true', help='store raw JSON output to debug.json')
parser.add_argument('--username', default=username, help='your Robinhood username')
parser.add_argument('--password', default=password, help='your Robinhood password')
args = parser.parse_args()
username = args.username
password = args.password

robinhood = Robinhood();

# login to Robinhood

if "ROBINHOOD" in os.environ:
    print os.environ["ROBINHOOD"]

while not logged_in:
    if username == "":
        print("Robinhood username:")
        try: input = raw_input
        except NameError: pass
        username = input()
    if password == "":
        password = getpass.getpass()

    logged_in = robinhood.login(username=username, password=password)
    if logged_in == False:
        password = ""
        print ("Invalid username or password.  Try again.\n")





# load a debug file
# raw_json = open('debug.txt','rU').read()
# orders = ast.literal_eval(raw_json)

# store debug
if args.debug:
    # save the CSV
    try:
        with open("debug.txt", "w+") as outfile:
            outfile.write(str(orders))
            print("Debug infomation written to debug.txt")
    except IOError:
        print('Oops.  Unable to write file to debug.txt')


def getData ():
    fields = collections.defaultdict(dict)
    nets = {}
    percentPositions = {}
    trade_count = 0
    queued_count = 0
    total = 0
    # fetch order history and related metadata from the Robinhood API
    orders = robinhood.get_endpoint('orders')
    positions = robinhood.get_endpoint('positions')
    dividends = robinhood.get_endpoint('dividends')
    total_equity = robinhood.get_endpoint('portfolios')['results'][0]['last_core_market_value']
    # do/while for pagination
    #pagination
    paginated = True
    page = 0
    n = 0

    #cache instruments
    cached_instruments = {} #{instrument:symbol}

    while paginated:
        for i, order in enumerate(orders['results']):
            executions = order['executions']
            if len(executions) > 0:
                trade_count += 1
                # Iterate over all the different executions
                for execution in executions:

                    # Get the Symbol of the order
                    fields[n]['symbol'] = cached_instruments.get(order['instrument'], robinhood.get_custom_endpoint(order['instrument'])['symbol'])
                    cached_instruments[order['instrument']] = fields[n]['symbol']

                    # Get all the key,value from the order
                    for key, value in enumerate(order):
                        if value != "executions":
                            fields[n][value] = order[value]

                    # Get specific values from the execution of the order
                    fields[n]['timestamp'] = execution['timestamp']
                    fields[n]['quantity'] = execution['quantity']
                    fields[n]['price'] = execution['price']
                    fields[n]['cost'] = float(fields[n]['quantity']) * float(fields[n]['price'])
                    if fields[n]['side'] == "buy" :
                        tradeNet = (float(fields[n]['cost']) + float(fields[n]['fees']))
                        total -= tradeNet
                        if fields[n]['symbol'] in nets :
                            nets[fields[n]['symbol']] -= tradeNet
                        else :
                            nets[fields[n]['symbol']] = tradeNet * (-1)
                    if fields[n]['side'] == "sell" :
                        tradeNet = (float(fields[n]['cost']) - float(fields[n]['fees']))
                        total += tradeNet
                        if fields[n]['symbol'] in nets :
                            nets[fields[n]['symbol']] += tradeNet
                        else :
                            nets[fields[n]['symbol']] = tradeNet
                    n+=1
            # If the state is queued, we keep this to let the user know they are pending orders
            elif order['state'] == "queued":
                queued_count += 1
        for i, position in enumerate(positions['results']):
            if position['quantity'] != '0.0000':
                fields[n]['symbol'] = cached_instruments.get(position['instrument'], robinhood.get_custom_endpoint(position['instrument'])['symbol'])
                fields[n]['side'] = "hold"
                fields[n]['timestamp'] = robinhood.get_custom_endpoint("https://api.robinhood.com/quotes/" + fields[n]['symbol'] + "/")['updated_at']
                fields[n]['quantity'] = position['quantity']
                fields[n]['price'] = robinhood.get_custom_endpoint("https://api.robinhood.com/quotes/" + fields[n]['symbol'] + "/")['last_extended_hours_trade_price']
                if str(fields[n]['price']) == 'None':
                    fields[n]['price'] = robinhood.get_custom_endpoint("https://api.robinhood.com/quotes/" + fields[n]['symbol'] + "/")['last_trade_price']
                fields[n]['cost'] = float(fields[n]['quantity']) * float(fields[n]['price'])
                total += float(fields[n]['cost'])
                if fields[n]['symbol'] in nets :
                    nets[fields[n]['symbol']] += float(fields[n]['cost'])
                else :
                    nets[fields[n]['symbol']] = float(fields[n]['cost'])
                percentPositions[fields[n]['symbol']] = float(fields[n]['cost']) * 100 / float(total_equity)
                n += 1
        for i, dividend in enumerate(dividends['results']):
            fields[n]['timestamp'] = dividend['paid_at']
            fields[n]['symbol'] = cached_instruments.get(dividend['instrument'], robinhood.get_custom_endpoint(dividend['instrument'])['symbol'])
            fields[n]['side'] = "dividend"
            fields[n]['cost'] = dividend['amount']
            total += float(fields[n]['cost'])
            if fields[n]['symbol'] in nets :
                nets[fields[n]['symbol']] += float(fields[n]['cost'])
            else :
                nets[fields[n]['symbol']] = float(fields[n]['cost'])
            n += 1



        # paginate, if out of ORDERS paginate is OVER
        if orders['next'] is not None:
            page = page + 1
            #get the next order, a page is essentially one order
            orders = robinhood.get_custom_endpoint(str(orders['next']))
        else:
            paginated = False
        printNets(nets, total)
        printEquities(percentPositions, total_equity)
        tradeData(trade_count, queued_count)
        printCSV(fields)

def printNets (nets, total):
    print "\nNet gain from each stock\n"
    for i in nets:
        print i, ("%.2f" % nets[i])
        print "----------"
    print 'net total'
    print total

def printEquities (percentPositions, total_equity):
    print "\nCurrent portfolio percentages\n"
    for i in percentPositions:
        print i, ("%.2f" % percentPositions[i])
        print "---------"
    print "total equity"
    print total_equity

#Fields stores ALL relevant information
# print nets

def tradeData (trade_count, queued_count):
    # check we have trade data to export
    if trade_count > 0 or queued_count > 0:
        print("%d queued trade%s and %d executed trade%s found in your account." % (queued_count, "s"[queued_count==1:], trade_count, "s"[trade_count==1:]))
        # print str(queued_count) + " queded trade(s) and " + str(trade_count) + " executed trade(s) found in your account."
    else:
        print("No trade history found in your account.")
        quit()


def printCSV (fields):
    # CSV headers

    desired = ("price", "timestamp", "fees", "quantity", "symbol", "side", "cost")

    #need to filter out the offending headers

    keys = fields[0].keys()
    keys = sorted(keys)
    newkeys = []
    for key in keys:
        if key in desired:
            newkeys.append(key)

    keys = list(newkeys)
    for i in range(0, len(newkeys)):
        if newkeys[i] == "price":
            newkeys[i] = "Purchase price per share"
        if newkeys[i] == "timestamp":
            newkeys[i] = "Date"
        if newkeys[i] == "fees":
            newkeys[i] = "Commission"
        if newkeys[i] == "quantity":
            newkeys[i] = "Shares"
        if newkeys[i] == "symbol":
            newkeys[i] = "Symbol"
        if newkeys[i] == "side":
            newkeys[i] = "Transaction type"
        if newkeys[i] == "cost":
            newkeys[i] = "Total Cost"

    csv = ""
    for key in newkeys:
        csv += key + ','
    csv += "\n"

    # CSV rows

    line = ""
    csvb = []

    for row in fields:
        for key in keys:
            try:
                if key=="price" or key=="fees" or key=="quantity":
                    fields[row][key] = round(float(fields[row][key]),2)
                line += str(fields[row][key]) + ","
            except:
                line += ","
        line += "\n"
        csvb.append(line)
        line = ""

    #google finance seems to prefer dates in ascending order, so we must reverse the given order
    for i in reversed(csvb):
        csv+=str(i)

    # choose a filename to save to
    print("Choose a filename or press enter to save to `robinhood.csv`:")
    try: input = raw_input
    except NameError: pass
    filename = input().strip()
    if filename == '':
        filename = "robinhood.csv"

    # save the CSV
    try:
        with open(filename, "w+") as outfile:
            outfile.write(csv)
    except IOError:
        print("Oops.  Unable to write file to ",filename)

getData()
