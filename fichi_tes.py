#!/bin/python3

import os
import sys
from time import time
import pytz
from datetime import datetime, timedelta
from optparse import OptionParser
import glob

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

import json

from operator import attrgetter

from woocommerce import API

global last_invoice_number
last_invoice_number = 0
current_tz = pytz.timezone('Europe/Paris')
date_time_input_ebay_format = '%Y-%m-%dT%H:%M:%S#!/bin/python3

import os
import sys
from time import time
import pytz
from datetime import datetime, timedelta
from optparse import OptionParser
import glob

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

import json

from operator import attrgetter

from woocommerce import API

global last_invoice_number
last_invoice_number = 0
current_tz = pytz.timezone('Europe/Paris')
date_time_input_ebay_format = '%Y-%m-%dT%H:%M:%S.%fZ'
date_time_request_ebay_format = '%Y-%m-%dT%H:%M:%S.000Z'
date_time_input_woocommerce_format = '%Y-%m-%dT%H:%M:%S'
date_time_output_format = '%d/%m/%Y %H:%M'

wcapi = API(
    url="https://lectix.fr",
    consumer_key="********",
    consumer_secret="********",
    version="wc/v3",
    timeout=20
)

# fetching product ref vs product ebay item ID
ref_dict = {}
ecopart_dict = {}
products_dir = glob.glob("../ebay/generateur-template/LEC*")

for product_path in products_dir:
    with open(product_path+'/ebay_ItemID.txt','r') as f:    # getting ebay item ID relatioship
        ItemID = f.read().replace('\n','')
        ref_dict[ItemID] = os.path.basename(product_path).upper()

    with open(product_path+'/eco-part.txt','r') as f:       # getting eco-part for each product
        eco_part = float(f.read().replace('\n',''))
        ecopart_dict[os.path.basename(product_path).upper()] = eco_part



class Address:
    def __init__(self, clientName = "UNK", company = None, street1 = None, street2 = None, postalCode = "", city = "", country = ""):
        self.clientName = clientName
        self.company = company
        self.street1 = street1
        self.street2 = street2
        self.postalCode = postalCode
        self.city = city
        self.country = country

    def get(self,linefeed = '\n'):
        ret_address = self.clientName + linefeed
        if(self.company != None and self.company != ""):
            ret_address += self.company + linefeed
        if(self.street1 != None and self.street1 != ""):
            ret_address += self.street1 + linefeed
        if(self.street2 != None and self.street2 != ""):
            ret_address += self.street2 + linefeed
        ret_address += self.postalCode + " " + self.city + linefeed
        ret_address += self.country

        return ret_address

    def __str__(self):
        return self.get()


class Transaction:
    def __init__(self):
        self.ID = ""
        self.qty = 0
        self.unitPriceHT = 0.0
        self.unitPriceTTC = 0.0
        self.unitReductionHT = 0.0
        self.unitReductionTTC = 0.0
        self.unitVAT = 0.0
        self.totalTTC = 0.0
        self.totalHT = 0.0
        self.ecoParticipation = 0.0

    def __str__(self):
        ret_str = "ID : %s\t"%(self.ID)
        ret_str += "qty : %s\t"%(self.qty)
        ret_str += "unit price HT : %.2f€\t"%(self.unitPriceHT)
        ret_str += "reduction HT : %.2f€\t"%(self.unitReductionHT)
        ret_str += "TVA 20%% : %.2f€\t"%(self.unitVAT)
        ret_str += "total TTC : %.2f€\n"%(self.totalTTC)
        return ret_str

    def get_latex(self):
        ret_str = ""
        # ret_str += "& & & & &\\\\\n"
        ret_str += self.ID + " & "
        ret_str += "%d"%(self.qty) + " & "
        ret_str += "%.2f"%(self.unitPriceTTC) + "€ & "
        ret_str += "%.2f"%(self.unitReductionTTC) + "€ & "
        ret_str += "%.2f"%(self.unitVAT) + "€ & "
        ret_str += "%.2f"%(self.totalTTC) + "€ \\\\\n"
        ret_str += " & "
        ret_str += " & "
        ret_str += "\\scriptsize{%.2f}"%(self.unitPriceHT) + "€ & "
        ret_str += "\\scriptsize{%.2f}"%(self.unitReductionHT) + "€ & "
        ret_str += " - & "
        ret_str += "\\scriptsize{%.2f}"%(self.totalHT) + "€ \\\\\n"
        if self.ecoParticipation > 0:
            ret_str += '\\it{\\scriptsize{dont éco-participation}} &  & \\scriptsize{%.2f€} &  &  & \\\\'%(self.ecoParticipation)
        ret_str += '\\hhline{------}'
        return ret_str

    def update(self):
        self.unitPriceHT = self.unitPriceTTC/1.2
        self.unitReductionHT = (self.unitPriceTTC + self.unitReductionTTC)/1.2 - self.unitPriceHT
        self.unitVAT = (self.unitPriceTTC + self.unitReductionTTC) - (self.unitPriceHT + self.unitReductionHT)
        self.totalTTC = self.qty * (self.unitPriceTTC + self.unitReductionTTC)
        self.totalHT = self.qty * (self.unitPriceHT + self.unitReductionHT)


class Transactions:
    def __init__(self):
        self.transactions = []
        self.subTotalHT = 0.0
        self.globalReduction = 0.0
        self.totalHT = 0.0
        self.totalVAT = 0.0
        self.totalTTC = 0.0

    def __str__(self):
        ret_str = "Transactions : \n"
        for tr in self.transactions:
            ret_str += str(tr)
        ret_str += "\t\t\t\t\tSous total HT : \t%.2f€\n"%(self.subTotalHT)
        ret_str += "\t\t\t\t\tRéduction HT : \t\t%.2f€\n"%(self.globalReduction)
        ret_str += "\t\t\t\t\tTotal HT : \t\t%.2f€\n"%(self.totalHT)
        ret_str += "\t\t\t\t\tTVA 20%% : \t\t%.2f€\n"%(self.totalVAT)
        ret_str += "\t\t\t\t\tTotal TTC : \t\t%.2f€\n"%(self.totalTTC)
        return ret_str

    def get_latex(self):
        ret_str = ""
        for tr in self.transactions:
            ret_str += tr.get_latex()
        return ret_str

    def update(self):
        self.subTotalHT = 0.0
        self.globalReduction = 0.0
        self.totalHT = 0.0
        self.totalVAT = 0.0
        self.totalTTC = 0.0
        for tr in self.transactions:
            tr.update()
            self.subTotalHT += (tr.qty * tr.unitPriceHT)
            self.globalReduction += (tr.qty * tr.unitReductionHT)
            self.totalVAT += (tr.qty * tr.unitVAT)

        self.totalHT = self.subTotalHT + self.globalReduction
        self.totalTTC = self.totalHT + self.totalVAT

    def add(self, tr):
        self.transactions.append(tr)
        self.update()


class InvoiceError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class Invoice:

    def __init__(self, prefix="EBA"):
        global date_time_output_format
        self.invoiceNumber = None
        self.orderID = ""
        self.buyerUserID = ""
        self.amountPaid = 0.0
        self.adjustmentAmount = 0.0
        self.amountSaved = 0.0
        self.issuedTime = None
        self.issuedTimestamp = 0
        self.paidTime = datetime.now(pytz.timezone('Europe/Paris')).strftime(date_time_output_format)
        self.address = Address()
        self.transactions = Transactions()
        self.prefix = prefix
        self.time = None

    def __str__(self):
        self.transactions.update()
        ret_str = '========== Invoice ==========\n'
        ret_str += 'invoice number : %s\n'%(self.invoiceNumber)
        ret_str += 'order ID : %s\n'%(self.orderID)
        ret_str += 'buyer user ID : %s\n'%(self.buyerUserID)
        ret_str += 'amount paid : %.2f\n'%(self.amountPaid)
        ret_str += 'adjustment amount : %.2f\n'%(self.adjustmentAmount)
        ret_str += 'amount saved : %.2f\n'%(self.amountSaved)
        ret_str += 'shipped time : %s\n'%(self.issuedTime)
        ret_str += 'paid time : %s\n'%(self.paidTime)
        ret_str += 'address : %s\n'%(self.address.get(' '))
        ret_str += str(self.transactions)
        ret_str += '=============================\n\n'
        return ret_str

    def get_invoice_number(self):
        if self.prefix == "EBA":
            with open("last_ebay_invoice_number",'r') as f:
                last_invoice_number = int(f.read())
                self.invoiceNumber = self.prefix+"%07d"%(last_invoice_number+1)
                return self.invoiceNumber
        elif self.prefix == "LEC":
            with open("last_woocommerce_invoice_number",'r') as f:
                last_invoice_number = int(f.read())
                self.invoiceNumber = self.prefix+"%07d"%(last_invoice_number+1)
                return self.invoiceNumber
        raise InvoiceError('Unknown invoice prefix','cannot get invoice number')

    def update_invoice_number(self):
        if self.prefix == "EBA":
            with open("last_ebay_invoice_number",'r') as f:
                last_invoice_number = int(f.read())
            with open("last_ebay_invoice_number",'w') as f:
                last_invoice_number += 1
                f.write("%d"%(last_invoice_number))
        elif self.prefix == "LEC":
            with open("last_woocommerce_invoice_number",'r') as f:
                last_invoice_number = int(f.read())
            with open("last_woocommerce_invoice_number",'w') as f:
                last_invoice_number += 1
                f.write("%d"%(last_invoice_number))
        else:
            raise InvoiceError('Unknown invoice prefix','cannot update invoice number')

    def get_invoice_title(self):
        if self.prefix == "EBA":
            invoice_title = "EBAY - " + self.buyerUserID.replace('_','\\_')
            return invoice_title
        elif self.prefix == "LEC":
            invoice_title = "LECTIX.FR - " + self.orderID
            return invoice_title
        raise InvoiceError('Unknown invoice prefix', 'cannot get invoice title')

    def generate(self):
        if "%.2f"%(self.adjustmentAmount) != "%.2f"%(0.0):
            tr = Transaction()
            tr.ID = "Ajustement"
            tr.qty = 1
            tr.unitPriceHT = self.adjustmentAmount/1.2
            tr.unitPriceTTC = self.adjustmentAmount
            tr.unitVAT = tr.unitPriceTTC - tr.unitPriceHT
            tr.unitReductionTTC = 0.0
            tr.ecoParticipation = 0.0
            self.add_transaction(tr)
        self.transactions.update()
        if "%.2f"%(self.transactions.totalTTC) != "%.2f"%(self.amountPaid):
            print('Total TTC (%.2f) différent du montant payé (%.2f)'%(self.transactions.totalTTC,self.amountPaid))
            print(self)
            exit()

        if self.invoiceNumber is None:
            self.get_invoice_number()

        if self.prefix == "EBA":
            output_filename = 'Invoices/Ebay/'+self.invoiceNumber+'_'+self.buyerUserID
        elif self.prefix == "LEC":
            output_filename = 'Invoices/Woocommerce/'+self.invoiceNumber+'_'+self.orderID
        else:
            raise InvoiceError('Unknown invoice prefix', 'Unknown invoice prefix')

        temp_filename = 'Invoice'
        with open(temp_filename+'.tex','w') as output_file:
            with open('invoice_template.tex','r') as invoice_template:
                invoice = invoice_template.read()
                invoice = invoice.replace('---ADRESSE-CLIENT---',self.address.get('\\\\\n'))
                invoice = invoice.replace('---TITRE-FACTURE---',self.get_invoice_title())
                invoice = invoice.replace('---NUMERO-FACTURE---',self.invoiceNumber)
                invoice = invoice.replace('---DATE-EMISSION---',self.issuedTime)
                invoice = invoice.replace('---DATE-PAIEMENT---',self.paidTime)
                invoice = invoice.replace('---ARTICLES---',self.transactions.get_latex())
                invoice = invoice.replace('---SOUS-TOTAL-HT---',"%.2f"%(self.transactions.subTotalHT))
                invoice = invoice.replace('---REDUCTION-GLOBALE---',"%.2f"%(self.transactions.globalReduction))
                invoice = invoice.replace('---TOTAL-HT---',"%.2f"%(self.transactions.totalHT))
                invoice = invoice.replace('---TOTAL-TVA---',"%.2f"%(self.transactions.totalVAT))
                invoice = invoice.replace('---TOTAL-TTC---',"%.2f"%(self.transactions.totalTTC))

                output_file.write(invoice)
        self.update_invoice_number()
        os.system('pdflatex '+temp_filename)
        os.rename(temp_filename+'.pdf',output_filename+'.pdf')

    def add_transaction(self, tr):
        self.transactions.add(tr)




def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-t", "--target",
                      dest="target", default="ebay",
                      help="choose target (ebay, woocommerce) [default: %default]")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")
    parser.add_option("-n", "--domain",
                      dest="domain", default='api.ebay.com',
                      help="Specifies the eBay domain to use (e.g. api.sandbox.ebay.com).")

    (opts, args) = parser.parse_args()
    return opts, args

def getOrders(opts):
    period = timedelta(days=89)
    date_from = datetime.today() - period
    date_to = datetime.today()

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid, domain=opts.domain,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20)

        api.execute('GetOrders', {'CreateTimeFrom': date_from.strftime(date_time_request_ebay_format),'CreateTimeTo': date_to.strftime(date_time_request_ebay_format)})
        # print(api.response.json())
        return api.response.json()

    except ConnectionError as e:
        print(e)
        print(e.response.dict())
        sys.exit(-1)



if __name__ == "__main__":
    (opts, args) = init_options()

    Invoices = []

    if opts.target == "ebay":

        with open('last_ebay_invoice_date','r') as f:
            last_ebay_invoice_date = datetime.strptime(f.read().replace('\n',''),date_time_input_ebay_format)
            last_ebay_invoice_date = current_tz.localize(last_ebay_invoice_date)
            print('last invoice date : %s'%(last_ebay_invoice_date.strftime(date_time_input_ebay_format)))

        most_recent_order_time = last_ebay_invoice_date

        orders = json.loads(getOrders(opts))
        with open("orders.txt","w") as f:
            f.write(json.dumps(orders, indent=4, sort_keys=True))
        # print(orders)

        for order in orders["OrderArray"]["Order"]:

            order_invoice = Invoice()
            order_invoice.orderID = order["OrderID"]
            order_invoice.buyerUserID = order["BuyerUserID"]
            order_invoice.adjustmentAmount = float(order["AdjustmentAmount"]["value"])
            order_invoice.amountPaid = float(order["AmountPaid"]["value"])
            order_invoice.amountSaved = float(order["AmountSaved"]["value"])
            try:
                if order["ShippedTime"] != order["CheckoutStatus"]["LastModifiedTime"]: # order was probably cancelled
                    if order["OrderStatus"] == "Cancelled":
                        order_time = datetime.strptime(order["CheckoutStatus"]["LastModifiedTime"],date_time_input_ebay_format)
                    elif order["OrderStatus"] == "Completed":
                        order_time = datetime.strptime(order["PaidTime"],date_time_input_ebay_format)
                    else:
                        print("Warning : shipped time differs from last modified time and the order status is not cancelled! ")
                        print(order)
                        exit()
                else:
                    order_time = datetime.strptime(order["PaidTime"],date_time_input_ebay_format)
            except Exception as e:
                if order["OrderStatus"] == "Cancelled": # the order was cancelled before it got shipped out
                    print("Ignoring order ID %s (Cancelled)"%(order["OrderID"]))
                    continue
                print(e)
                print("This exception occured during the parsing of the following data :")
                print(order)
                continue

            order_time = pytz.timezone('UTC').localize(order_time)
            order_time = order_time.astimezone(current_tz)
            order_invoice.issuedTimestamp = datetime.timestamp(order_time)
            order_invoice.issuedTime = order_time.strftime(date_time_output_format)


            if order_time <= last_ebay_invoice_date:
                print('Ignoring invoice from %s'%(order_invoice.paidTime))
                continue

            if most_recent_order_time < order_time:
                most_recent_order_time = order_time

            payment_time = datetime.strptime(order["PaidTime"],date_time_input_ebay_format)
            payment_time = pytz.timezone('UTC').localize(payment_time)
            payment_time = payment_time.astimezone(current_tz)
            order_invoice.time = payment_time
            order_invoice.paidTime = payment_time.strftime(date_time_output_format)

            order_invoice.address = Address(order["ShippingAddress"]["Name"])
            order_invoice.address.street1 = order["ShippingAddress"]["Street1"]
            order_invoice.address.street2 = order["ShippingAddress"]["Street2"]
            order_invoice.address.postalCode = order["ShippingAddress"]["PostalCode"]
            order_invoice.address.city = order["ShippingAddress"]["CityName"]
            order_invoice.address.country = order["ShippingAddress"]["Country"]

            if order["OrderStatus"] == "Cancelled":
                tr = Transaction()
                tr.ID = "Remboursement"
                tr.qty = 1

                tr.unitPriceTTC = float(order["AdjustmentAmount"]["value"])
                tr.unitReductionTTC = 0.0

                tr.ecoParticipation = 0
                order_invoice.add_transaction(tr)
            else:
                for transaction in order["TransactionArray"]["Transaction"]:
                    tr = Transaction()
                    tr.ID = ref_dict[transaction["Item"]["ItemID"]]
                    tr.qty = int(transaction["QuantityPurchased"])

                    try:
                        tr.unitPriceTTC = float(transaction["SellerDiscounts"]["OriginalItemPrice"]["value"])
                    except:
                        tr.unitPriceTTC = float(transaction["TransactionPrice"]["value"])
                    try:
                        tr.unitReductionTTC = float(transaction["SellerDiscounts"]["SellerDiscount"]["ItemDiscountAmount"]["value"]) - float(transaction["SellerDiscounts"]["OriginalItemPrice"]["value"])
                    except:
                        tr.unitReductionTTC = 0.0

                    tr.ecoParticipation = ecopart_dict[tr.ID]
                    order_invoice.add_transaction(tr)

                if order["ShippingServiceSelected"]["ShippingServiceCost"]["value"] != "0.0":
                    tr = Transaction()
                    tr.ID = "Frais de livraison"
                    tr.qty = 1
                    tr.unitPriceTTC = float(order["ShippingServiceSelected"]["ShippingServiceCost"]["value"])
                    tr.unitReductionTTC = 0.0
                    order_invoice.add_transaction(tr)

            Invoices.append(order_invoice)

    elif opts.target == "woocommerce":
        print("Fetching orders from woocommerce")

        with open('last_woocommerce_invoice_date','r') as f:
            last_woocommerce_invoice_date = datetime.strptime(f.read().replace('\n',''),date_time_input_woocommerce_format)
            last_woocommerce_invoice_date = current_tz.localize(last_woocommerce_invoice_date)
            print('last invoice date : %s'%(last_woocommerce_invoice_date.strftime(date_time_input_woocommerce_format)))

        most_recent_order_time = last_woocommerce_invoice_date

        r = wcapi.get("orders?per_page=100")
        orders = r.json()
        # with open("wc-orders.json","w") as f:
        #     f.write(str(orders))
        for order in orders:
            if order["status"] != "completed":
                continue
            print("Fetched order %d -> %s"%(order["id"],order["status"]))
            order_invoice = Invoice("LEC")
            order_invoice.orderID = str(order["id"])
            order_invoice.amountPaid = float(order["total"])
            order_invoice.amountSaved = float(order["discount_total"])

            order_time = datetime.strptime(order["date_completed"],date_time_input_woocommerce_format)
            order_time = pytz.timezone('UTC').localize(order_time)
            order_time = order_time.astimezone(current_tz)
            order_invoice.issuedTimestamp = datetime.timestamp(order_time)
            order_invoice.issuedTime = order_time.strftime(date_time_output_format)

            payment_time = datetime.strptime(order["date_paid"],date_time_input_woocommerce_format)
            payment_time = pytz.timezone('UTC').localize(payment_time)
            payment_time = payment_time.astimezone(current_tz)
            order_invoice.time = payment_time
            order_invoice.paidTime = payment_time.strftime(date_time_output_format)

            if payment_time <= last_woocommerce_invoice_date:
                print('Ignoring invoice from %s'%(order_invoice.paidTime))
                continue

            if most_recent_order_time < payment_time:
                most_recent_order_time = payment_time

            order_invoice.address = Address(order["billing"]["first_name"] + ' ' + order["billing"]["last_name"])
            order_invoice.address.company = order["billing"]["company"]
            order_invoice.address.street1 = order["billing"]["address_1"]
            order_invoice.address.street2 = order["billing"]["address_2"]
            order_invoice.address.postalCode = order["billing"]["postcode"]
            order_invoice.address.city = order["billing"]["city"]
            order_invoice.address.country = order["billing"]["country"]


            for transaction in order["line_items"]:
                tr = Transaction()
                tr.ID = transaction["sku"]
                tr.qty = int(transaction["quantity"])
                tr.unitVAT = float(transaction["subtotal_tax"]) / tr.qty
                tr.unitPriceHT = float(transaction["subtotal"]) / tr.qty
                tr.unitPriceTTC = tr.unitPriceHT + tr.unitVAT
                tr.unitReductionTTC = (float(transaction["total"]) + float(transaction["total_tax"]) - float(transaction["subtotal"]) - float(transaction["subtotal_tax"])) / tr.qty

                # try:
                #     tr.unitPriceTTC = float(transaction["meta_data"]["value"]["initial_price"])
                # except:
                #     tr.unitPriceTTC = float(transaction["price"])
                # try:
                #     tr.unitReductionTTC = tr.unitPriceTTC - float(transaction["meta_data"]["value"]["discounted_price"])
                # except:
                #     tr.unitReductionTTC = 0.0

                tr.ecoParticipation = ecopart_dict[tr.ID]
                order_invoice.add_transaction(tr)
            Invoices.append(order_invoice)
    else :
        print("Error : %s is not a valid target!"%(opts.target))
        sys.exit(-1)

    sorted_invoices = sorted(Invoices,key=attrgetter('issuedTimestamp'))

    for inv in sorted_invoices:
        print("%s -> %s"%(inv.issuedTime,inv.buyerUserID))
        # print(inv)
        inv.generate()

        # write last invoice time so that we keep track of the ones already generated if a bug occurs during the generation of a new one
        if opts.target == "ebay":
            with open('last_ebay_invoice_date','w') as f:
                f.write(inv.time.strftime(date_time_input_ebay_format))
        elif opts.target == "woocommerce":
            with open('last_woocommerce_invoice_date','w') as f:
                f.write(inv.time.strftime(date_time_input_woocommerce_format))

    if len(sorted_invoices)==0:
        print("No invoice to generate!")
.%fZ'
date_time_request_ebay_format = '%Y-%m-%dT%H:%M:%S.000Z'
date_time_input_woocommerce_format = '%Y-%m-%dT%H:%M:%S'
date_time_output_format = '%d/%m/%Y %H:%M'

wcapi = API(
    url="https://lectix.fr",
    consumer_key="********",
    consumer_secret="********",
    version="wc/v3",
    timeout=20
)

# fetching product ref vs product ebay item ID
ref_dict = {}
ecopart_dict = {}
products_dir = glob.glob("../ebay/generateur-template/LEC*")

for product_path in products_dir:
    with open(product_path + '/ebay_ItemID.txt', 'r') as f:  # getting ebay item ID relatioship
        ItemID = f.read().replace('\n', '')
        ref_dict[ItemID] = os.path.basename(product_path).upper()

    with open(product_path + '/eco-part.txt', 'r') as f:  # getting eco-part for each product
        eco_part = float(f.read().replace('\n', ''))
        ecopart_dict[os.path.basename(product_path).upper()] = eco_part


class Address:
    def __init__(self, clientName="UNK", company=None, street1=None, street2=None, postalCode="", city="", country=""):
        self.clientName = clientName
        self.company = company
        self.street1 = street1
        self.street2 = street2
        self.postalCode = postalCode
        self.city = city
        self.country = country

    def get(self, linefeed='\n'):
        ret_address = self.clientName + linefeed
        if (self.company != None and self.company != ""):
            ret_address += self.company + linefeed
        if (self.street1 != None and self.street1 != ""):
            ret_address += self.street1 + linefeed
        if (self.street2 != None and self.street2 != ""):
            ret_address += self.street2 + linefeed
        ret_address += self.postalCode + " " + self.city + linefeed
        ret_address += self.country

        return ret_address

    def __str__(self):
        return self.get()


class Transaction:
    def __init__(self):
        self.ID = ""
        self.qty = 0
        self.unitPriceHT = 0.0
        self.unitPriceTTC = 0.0
        self.unitReductionHT = 0.0
        self.unitReductionTTC = 0.0
        self.unitVAT = 0.0
        self.totalTTC = 0.0
        self.totalHT = 0.0
        self.ecoParticipation = 0.0

    def __str__(self):
        ret_str = "ID : %s\t" % (self.ID)
        ret_str += "qty : %s\t" % (self.qty)
        ret_str += "unit price HT : %.2f€\t" % (self.unitPriceHT)
        ret_str += "reduction HT : %.2f€\t" % (self.unitReductionHT)
        ret_str += "TVA 20%% : %.2f€\t" % (self.unitVAT)
        ret_str += "total TTC : %.2f€\n" % (self.totalTTC)
        return ret_str

    def get_latex(self):
        ret_str = ""
        # ret_str += "& & & & &\\\\\n"
        ret_str += self.ID + " & "
        ret_str += "%d" % (self.qty) + " & "
        ret_str += "%.2f" % (self.unitPriceTTC) + "€ & "
        ret_str += "%.2f" % (self.unitReductionTTC) + "€ & "
        ret_str += "%.2f" % (self.unitVAT) + "€ & "
        ret_str += "%.2f" % (self.totalTTC) + "€ \\\\\n"
        ret_str += " & "
        ret_str += " & "
        ret_str += "\\scriptsize{%.2f}" % (self.unitPriceHT) + "€ & "
        ret_str += "\\scriptsize{%.2f}" % (self.unitReductionHT) + "€ & "
        ret_str += " - & "
        ret_str += "\\scriptsize{%.2f}" % (self.totalHT) + "€ \\\\\n"
        if self.ecoParticipation > 0:
            ret_str += '\\it{\\scriptsize{dont éco-participation}} &  & \\scriptsize{%.2f€} &  &  & \\\\' % (
                self.ecoParticipation)
        ret_str += '\\hhline{------}'
        return ret_str

    def update(self):
        self.unitPriceHT = self.unitPriceTTC / 1.2
        self.unitReductionHT = (self.unitPriceTTC + self.unitReductionTTC) / 1.2 - self.unitPriceHT
        self.unitVAT = (self.unitPriceTTC + self.unitReductionTTC) - (self.unitPriceHT + self.unitReductionHT)
        self.totalTTC = self.qty * (self.unitPriceTTC + self.unitReductionTTC)
        self.totalHT = self.qty * (self.unitPriceHT + self.unitReductionHT)


class Transactions:
    def __init__(self):
        self.transactions = []
        self.subTotalHT = 0.0
        self.globalReduction = 0.0
        self.totalHT = 0.0
        self.totalVAT = 0.0
        self.totalTTC = 0.0

    def __str__(self):
        ret_str = "Transactions : \n"
        for tr in self.transactions:
            ret_str += str(tr)
        ret_str += "\t\t\t\t\tSous total HT : \t%.2f€\n" % (self.subTotalHT)
        ret_str += "\t\t\t\t\tRéduction HT : \t\t%.2f€\n" % (self.globalReduction)
        ret_str += "\t\t\t\t\tTotal HT : \t\t%.2f€\n" % (self.totalHT)
        ret_str += "\t\t\t\t\tTVA 20%% : \t\t%.2f€\n" % (self.totalVAT)
        ret_str += "\t\t\t\t\tTotal TTC : \t\t%.2f€\n" % (self.totalTTC)
        return ret_str

    def get_latex(self):
        ret_str = ""
        for tr in self.transactions:
            ret_str += tr.get_latex()
        return ret_str

    def update(self):
        self.subTotalHT = 0.0
        self.globalReduction = 0.0
        self.totalHT = 0.0
        self.totalVAT = 0.0
        self.totalTTC = 0.0
        for tr in self.transactions:
            tr.update()
            self.subTotalHT += (tr.qty * tr.unitPriceHT)
            self.globalReduction += (tr.qty * tr.unitReductionHT)
            self.totalVAT += (tr.qty * tr.unitVAT)

        self.totalHT = self.subTotalHT + self.globalReduction
        self.totalTTC = self.totalHT + self.totalVAT

    def add(self, tr):
        self.transactions.append(tr)
        self.update()


class InvoiceError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class Invoice:

    def __init__(self, prefix="EBA"):
        global date_time_output_format
        self.invoiceNumber = None
        self.orderID = ""
        self.buyerUserID = ""
        self.amountPaid = 0.0
        self.adjustmentAmount = 0.0
        self.amountSaved = 0.0
        self.issuedTime = None
        self.issuedTimestamp = 0
        self.paidTime = datetime.now(pytz.timezone('Europe/Paris')).strftime(date_time_output_format)
        self.address = Address()
        self.transactions = Transactions()
        self.prefix = prefix
        self.time = None

    def __str__(self):
        self.transactions.update()
        ret_str = '========== Invoice ==========\n'
        ret_str += 'invoice number : %s\n' % (self.invoiceNumber)
        ret_str += 'order ID : %s\n' % (self.orderID)
        ret_str += 'buyer user ID : %s\n' % (self.buyerUserID)
        ret_str += 'amount paid : %.2f\n' % (self.amountPaid)
        ret_str += 'adjustment amount : %.2f\n' % (self.adjustmentAmount)
        ret_str += 'amount saved : %.2f\n' % (self.amountSaved)
        ret_str += 'shipped time : %s\n' % (self.issuedTime)
        ret_str += 'paid time : %s\n' % (self.paidTime)
        ret_str += 'address : %s\n' % (self.address.get(' '))
        ret_str += str(self.transactions)
        ret_str += '=============================\n\n'
        return ret_str

    def get_invoice_number(self):
        if self.prefix == "EBA":
            with open("last_ebay_invoice_number", 'r') as f:
                last_invoice_number = int(f.read())
                self.invoiceNumber = self.prefix + "%07d" % (last_invoice_number + 1)
                return self.invoiceNumber
        elif self.prefix == "LEC":
            with open("last_woocommerce_invoice_number", 'r') as f:
                last_invoice_number = int(f.read())
                self.invoiceNumber = self.prefix + "%07d" % (last_invoice_number + 1)
                return self.invoiceNumber
        raise InvoiceError('Unknown invoice prefix', 'cannot get invoice number')

    def update_invoice_number(self):
        if self.prefix == "EBA":
            with open("last_ebay_invoice_number", 'r') as f:
                last_invoice_number = int(f.read())
            with open("last_ebay_invoice_number", 'w') as f:
                last_invoice_number += 1
                f.write("%d" % (last_invoice_number))
        elif self.prefix == "LEC":
            with open("last_woocommerce_invoice_number", 'r') as f:
                last_invoice_number = int(f.read())
            with open("last_woocommerce_invoice_number", 'w') as f:
                last_invoice_number += 1
                f.write("%d" % (last_invoice_number))
        else:
            raise InvoiceError('Unknown invoice prefix', 'cannot update invoice number')

    def get_invoice_title(self):
        if self.prefix == "EBA":
            invoice_title = "EBAY - " + self.buyerUserID.replace('_', '\\_')
            return invoice_title
        elif self.prefix == "LEC":
            invoice_title = "LECTIX.FR - " + self.orderID
            return invoice_title
        raise InvoiceError('Unknown invoice prefix', 'cannot get invoice title')

    def generate(self):
        if "%.2f" % (self.adjustmentAmount) != "%.2f" % (0.0):
            tr = Transaction()
            tr.ID = "Ajustement"
            tr.qty = 1
            tr.unitPriceHT = self.adjustmentAmount / 1.2
            tr.unitPriceTTC = self.adjustmentAmount
            tr.unitVAT = tr.unitPriceTTC - tr.unitPriceHT
            tr.unitReductionTTC = 0.0
            tr.ecoParticipation = 0.0
            self.add_transaction(tr)
        self.transactions.update()
        if "%.2f" % (self.transactions.totalTTC) != "%.2f" % (self.amountPaid):
            print('Total TTC (%.2f) différent du montant payé (%.2f)' % (self.transactions.totalTTC, self.amountPaid))
            print(self)
            exit()

        if self.invoiceNumber is None:
            self.get_invoice_number()

        if self.prefix == "EBA":
            output_filename = 'Invoices/Ebay/' + self.invoiceNumber + '_' + self.buyerUserID
        elif self.prefix == "LEC":
            output_filename = 'Invoices/Woocommerce/' + self.invoiceNumber + '_' + self.orderID
        else:
            raise InvoiceError('Unknown invoice prefix', 'Unknown invoice prefix')

        temp_filename = 'Invoice'
        with open(temp_filename + '.tex', 'w') as output_file:
            with open('invoice_template.tex', 'r') as invoice_template:
                invoice = invoice_template.read()
                invoice = invoice.replace('---ADRESSE-CLIENT---', self.address.get('\\\\\n'))
                invoice = invoice.replace('---TITRE-FACTURE---', self.get_invoice_title())
                invoice = invoice.replace('---NUMERO-FACTURE---', self.invoiceNumber)
                invoice = invoice.replace('---DATE-EMISSION---', self.issuedTime)
                invoice = invoice.replace('---DATE-PAIEMENT---', self.paidTime)
                invoice = invoice.replace('---ARTICLES---', self.transactions.get_latex())
                invoice = invoice.replace('---SOUS-TOTAL-HT---', "%.2f" % (self.transactions.subTotalHT))
                invoice = invoice.replace('---REDUCTION-GLOBALE---', "%.2f" % (self.transactions.globalReduction))
                invoice = invoice.replace('---TOTAL-HT---', "%.2f" % (self.transactions.totalHT))
                invoice = invoice.replace('---TOTAL-TVA---', "%.2f" % (self.transactions.totalVAT))
                invoice = invoice.replace('---TOTAL-TTC---', "%.2f" % (self.transactions.totalTTC))

                output_file.write(invoice)
        self.update_invoice_number()
        os.system('pdflatex ' + temp_filename)
        os.rename(temp_filename + '.pdf', output_filename + '.pdf')

    def add_transaction(self, tr):
        self.transactions.add(tr)


def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-t", "--target",
                      dest="target", default="ebay",
                      help="choose target (ebay, woocommerce) [default: %default]")
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")
    parser.add_option("-n", "--domain",
                      dest="domain", default='api.ebay.com',
                      help="Specifies the eBay domain to use (e.g. api.sandbox.ebay.com).")

    (opts, args) = parser.parse_args()
    return opts, args


def getOrders(opts):
    period = timedelta(days=89)
    date_from = datetime.today() - period
    date_to = datetime.today()

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid, domain=opts.domain,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20)

        api.execute('GetOrders', {'CreateTimeFrom': date_from.strftime(date_time_request_ebay_format),
                                  'CreateTimeTo': date_to.strftime(date_time_request_ebay_format)})
        # print(api.response.json())
        return api.response.json()

    except ConnectionError as e:
        print(e)
        print(e.response.dict())
        sys.exit(-1)


if __name__ == "__main__":
    (opts, args) = init_options()

    Invoices = []

    if opts.target == "ebay":

        with open('last_ebay_invoice_date', 'r') as f:
            last_ebay_invoice_date = datetime.strptime(f.read().replace('\n', ''), date_time_input_ebay_format)
            last_ebay_invoice_date = current_tz.localize(last_ebay_invoice_date)
            print('last invoice date : %s' % (last_ebay_invoice_date.strftime(date_time_input_ebay_format)))

        most_recent_order_time = last_ebay_invoice_date

        orders = json.loads(getOrders(opts))
        with open("orders.txt", "w") as f:
            f.write(json.dumps(orders, indent=4, sort_keys=True))
        # print(orders)

        for order in orders["OrderArray"]["Order"]:

            order_invoice = Invoice()
            order_invoice.orderID = order["OrderID"]
            order_invoice.buyerUserID = order["BuyerUserID"]
            order_invoice.adjustmentAmount = float(order["AdjustmentAmount"]["value"])
            order_invoice.amountPaid = float(order["AmountPaid"]["value"])
            order_invoice.amountSaved = float(order["AmountSaved"]["value"])
            try:
                if order["ShippedTime"] != order["CheckoutStatus"]["LastModifiedTime"]:  # order was probably cancelled
                    if order["OrderStatus"] == "Cancelled":
                        order_time = datetime.strptime(order["CheckoutStatus"]["LastModifiedTime"],
                                                       date_time_input_ebay_format)
                    elif order["OrderStatus"] == "Completed":
                        order_time = datetime.strptime(order["PaidTime"], date_time_input_ebay_format)
                    else:
                        print(
                            "Warning : shipped time differs from last modified time and the order status is not cancelled! ")
                        print(order)
                        exit()
                else:
                    order_time = datetime.strptime(order["PaidTime"], date_time_input_ebay_format)
            except Exception as e:
                if order["OrderStatus"] == "Cancelled":  # the order was cancelled before it got shipped out
                    print("Ignoring order ID %s (Cancelled)" % (order["OrderID"]))
                    continue
                print(e)
                print("This exception occured during the parsing of the following data :")
                print(order)
                continue

            order_time = pytz.timezone('UTC').localize(order_time)
            order_time = order_time.astimezone(current_tz)
            order_invoice.issuedTimestamp = datetime.timestamp(order_time)
            order_invoice.issuedTime = order_time.strftime(date_time_output_format)

            if order_time <= last_ebay_invoice_date:
                print('Ignoring invoice from %s' % (order_invoice.paidTime))
                continue

            if most_recent_order_time < order_time:
                most_recent_order_time = order_time

            payment_time = datetime.strptime(order["PaidTime"], date_time_input_ebay_format)
            payment_time = pytz.timezone('UTC').localize(payment_time)
            payment_time = payment_time.astimezone(current_tz)
            order_invoice.time = payment_time
            order_invoice.paidTime = payment_time.strftime(date_time_output_format)

            order_invoice.address = Address(order["ShippingAddress"]["Name"])
            order_invoice.address.street1 = order["ShippingAddress"]["Street1"]
            order_invoice.address.street2 = order["ShippingAddress"]["Street2"]
            order_invoice.address.postalCode = order["ShippingAddress"]["PostalCode"]
            order_invoice.address.city = order["ShippingAddress"]["CityName"]
            order_invoice.address.country = order["ShippingAddress"]["Country"]

            if order["OrderStatus"] == "Cancelled":
                tr = Transaction()
                tr.ID = "Remboursement"
                tr.qty = 1

                tr.unitPriceTTC = float(order["AdjustmentAmount"]["value"])
                tr.unitReductionTTC = 0.0

                tr.ecoParticipation = 0
                order_invoice.add_transaction(tr)
            else:
                for transaction in order["TransactionArray"]["Transaction"]:
                    tr = Transaction()
                    tr.ID = ref_dict[transaction["Item"]["ItemID"]]
                    tr.qty = int(transaction["QuantityPurchased"])

                    try:
                        tr.unitPriceTTC = float(transaction["SellerDiscounts"]["OriginalItemPrice"]["value"])
                    except:
                        tr.unitPriceTTC = float(transaction["TransactionPrice"]["value"])
                    try:
                        tr.unitReductionTTC = float(
                            transaction["SellerDiscounts"]["SellerDiscount"]["ItemDiscountAmount"]["value"]) - float(
                            transaction["SellerDiscounts"]["OriginalItemPrice"]["value"])
                    except:
                        tr.unitReductionTTC = 0.0

                    tr.ecoParticipation = ecopart_dict[tr.ID]
                    order_invoice.add_transaction(tr)

                if order["ShippingServiceSelected"]["ShippingServiceCost"]["value"] != "0.0":
                    tr = Transaction()
                    tr.ID = "Frais de livraison"
                    tr.qty = 1
                    tr.unitPriceTTC = float(order["ShippingServiceSelected"]["ShippingServiceCost"]["value"])
                    tr.unitReductionTTC = 0.0
                    order_invoice.add_transaction(tr)

            Invoices.append(order_invoice)

    elif opts.target == "woocommerce":
        print("Fetching orders from woocommerce")

        with open('last_woocommerce_invoice_date', 'r') as f:
            last_woocommerce_invoice_date = datetime.strptime(f.read().replace('\n', ''),
                                                              date_time_input_woocommerce_format)
            last_woocommerce_invoice_date = current_tz.localize(last_woocommerce_invoice_date)
            print(
                'last invoice date : %s' % (last_woocommerce_invoice_date.strftime(date_time_input_woocommerce_format)))

        most_recent_order_time = last_woocommerce_invoice_date

        r = wcapi.get("orders?per_page=100")
        orders = r.json()
        # with open("wc-orders.json","w") as f:
        #     f.write(str(orders))
        for order in orders:
            if order["status"] != "completed":
                continue
            print("Fetched order %d -> %s" % (order["id"], order["status"]))
            order_invoice = Invoice("LEC")
            order_invoice.orderID = str(order["id"])
            order_invoice.amountPaid = float(order["total"])
            order_invoice.amountSaved = float(order["discount_total"])

            order_time = datetime.strptime(order["date_completed"], date_time_input_woocommerce_format)
            order_time = pytz.timezone('UTC').localize(order_time)
            order_time = order_time.astimezone(current_tz)
            order_invoice.issuedTimestamp = datetime.timestamp(order_time)
            order_invoice.issuedTime = order_time.strftime(date_time_output_format)

            payment_time = datetime.strptime(order["date_paid"], date_time_input_woocommerce_format)
            payment_time = pytz.timezone('UTC').localize(payment_time)
            payment_time = payment_time.astimezone(current_tz)
            order_invoice.time = payment_time
            order_invoice.paidTime = payment_time.strftime(date_time_output_format)

            if payment_time <= last_woocommerce_invoice_date:
                print('Ignoring invoice from %s' % (order_invoice.paidTime))
                continue

            if most_recent_order_time < payment_time:
                most_recent_order_time = payment_time

            order_invoice.address = Address(order["billing"]["first_name"] + ' ' + order["billing"]["last_name"])
            order_invoice.address.company = order["billing"]["company"]
            order_invoice.address.street1 = order["billing"]["address_1"]
            order_invoice.address.street2 = order["billing"]["address_2"]
            order_invoice.address.postalCode = order["billing"]["postcode"]
            order_invoice.address.city = order["billing"]["city"]
            order_invoice.address.country = order["billing"]["country"]

            for transaction in order["line_items"]:
                tr = Transaction()
                tr.ID = transaction["sku"]
                tr.qty = int(transaction["quantity"])
                tr.unitVAT = float(transaction["subtotal_tax"]) / tr.qty
                tr.unitPriceHT = float(transaction["subtotal"]) / tr.qty
                tr.unitPriceTTC = tr.unitPriceHT + tr.unitVAT
                tr.unitReductionTTC = (float(transaction["total"]) + float(transaction["total_tax"]) - float(
                    transaction["subtotal"]) - float(transaction["subtotal_tax"])) / tr.qty

                # try:
                #     tr.unitPriceTTC = float(transaction["meta_data"]["value"]["initial_price"])
                # except:
                #     tr.unitPriceTTC = float(transaction["price"])
                # try:
                #     tr.unitReductionTTC = tr.unitPriceTTC - float(transaction["meta_data"]["value"]["discounted_price"])
                # except:
                #     tr.unitReductionTTC = 0.0

                tr.ecoParticipation = ecopart_dict[tr.ID]
                order_invoice.add_transaction(tr)
            Invoices.append(order_invoice)
    else:
        print("Error : %s is not a valid target!" % (opts.target))
        sys.exit(-1)

    sorted_invoices = sorted(Invoices, key=attrgetter('issuedTimestamp'))

    for inv in sorted_invoices:
        print("%s -> %s" % (inv.issuedTime, inv.buyerUserID))
        # print(inv)
        inv.generate()

        # write last invoice time so that we keep track of the ones already generated if a bug occurs during the generation of a new one
        if opts.target == "ebay":
            with open('last_ebay_invoice_date', 'w') as f:
                f.write(inv.time.strftime(date_time_input_ebay_format))
        elif opts.target == "woocommerce":
            with open('last_woocommerce_invoice_date', 'w') as f:
                f.write(inv.time.strftime(date_time_input_woocommerce_format))

    if len(sorted_invoices) == 0:
        print("No invoice to generate!")
