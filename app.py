# coding=utf-8
from __future__ import print_function

import argparse

from flask import Flask, render_template, request, jsonify, Response

import glob
from cStringIO import StringIO

import time
import calendar
from datetime import datetime
import xml.etree.ElementTree as ET

import csv
from unicode_csv import UnicodeWriter

namespaces = {
    'c': 'http://xbrl.dcca.dk/gsd',
    'd': 'http://xbrl.dcca.dk/fsa',
    'g': 'http://xbrl.dcca.dk/arr',
    #http://www.xbrl.org/2003/instance
}
# tagname_cvr = # '{http://xbrl.dcca.dk/gsd}IdentificationNumberCvrOfSubmittingEnterprise' # Not all files contains this
tagname_cvr = '{http://xbrl.dcca.dk/gsd}IdentificationNumberCvrOfReportingEntity'
tagname_companyname = '{http://xbrl.dcca.dk/gsd}NameOfReportingEntity'
tagname_address = '{http://xbrl.dcca.dk/gsd}AddressOfSubmittingEnterpriseStreetAndNumber'
tagname_city = '{http://xbrl.dcca.dk/gsd}AddressOfSubmittingEnterprisePostcodeAndTown'
# tagname_auditor ='{http://xbrl.dcca.dk/gsd}NameOfAuditFirm'

fields = {
    'tagname_grossprofitloss': '{http://xbrl.dcca.dk/fsa}GrossProfitLoss',
    'Overskud/Tab': '{http://xbrl.dcca.dk/fsa}ProfitLoss',
    'Indtjening': '{http://xbrl.dcca.dk/fsa}Revenue',
    'Skat': '{http://xbrl.dcca.dk/fsa}TaxExpense',
    'Egenkapital': '{http://xbrl.dcca.dk/fsa}Equity',
    'Lønninger': '{http://xbrl.dcca.dk/fsa}WagesAndSalaries',
    'Grunde og bygninger': '{http://xbrl.dcca.dk/fsa}LandAndBuildings',
    'Andre indtægter': '{http://xbrl.dcca.dk/fsa}OtherFinanceIncome',
    'Andre udgifter': '{http://xbrl.dcca.dk/fsa}OtherFinanceExpenses',
}

tagname_context = '{http://www.xbrl.org/2003/instance}context'


all_companies = []
company_dictionary = {}


def unixtimestamp(d):
    #return time.mktime(d.timetuple())
    #print(d.utctimetuple())
    return calendar.timegm(d.utctimetuple())


class Company():

    def __init__(self, cvr, name, address, city):
        self.cvr = cvr
        self.name = name
        self.city = city
        self.address = address
        # self.auditor = None

        self.contexts = []

    def to_dict(self):
        contexts = {}
        for c in self.contexts:
            if c.fields:
                contexts[c.year] = c.to_dict()

        return {
           'cvr': self.cvr,
           'name': self.name,
           'city': self.city,
           'address': self.address,
           # auditor': self.auditor,
           'regnskaber': contexts
        }


class TimeContext():
    def __init__(self):
        self.start_date = None
        self.end_date = None
        self.instant_date = None
        self.year = None
        self.fields = {}
        self.context_id = {}

    @classmethod
    def fromXmlNode(cls, node):
        node_period = node.find('{http://www.xbrl.org/2003/instance}period')
        if node_period is None:
            return None

        self = cls()
        self.fields = {}
        self.context_id = node.get('id')

        if node_period.find('{http://www.xbrl.org/2003/instance}instant') is not None:
            self.instant_date = unixtimestamp(datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}instant').text, '%Y-%m-%d'))
            self.year = datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}instant').text, '%Y-%m-%d').year
        elif node_period.find('{http://www.xbrl.org/2003/instance}startDate') is not None and \
             node_period.find('{http://www.xbrl.org/2003/instance}endDate') is not None:
            self.start_date = unixtimestamp(datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}startDate').text, '%Y-%m-%d'))
            self.end_date   = unixtimestamp(datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}endDate').text, '%Y-%m-%d'))
            self.year = datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}startDate').text, '%Y-%m-%d').year
        return self

    def to_dict(self):
        d = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'instant_date': self.instant_date,
            'year': self.year,
            'context_id': self.context_id,
            'fields': self.fields
        }
        return d


for filename in glob.glob('aarsregnskaber/*.xml'):
    with open(filename, 'r') as f:
        dom = ET.parse(f)
        root = dom.getroot()

        # Get CVR
        cvr = root.find(tagname_cvr, namespaces=namespaces).text
        companyname = root.find(tagname_companyname, namespaces=namespaces).text
        # auditor = root.find(tagname_auditor, namespaces=namespaces).text
        address = root.find(tagname_address, namespaces=namespaces).text
        city = root.find(tagname_city, namespaces=namespaces).text

        company = Company(
          cvr=cvr,
          name=companyname,
          # auditor=auditor,
          address=address,
          city=city
        )
        all_companies.append(company)
        company_dictionary[company.cvr] = company

        # build contexts
        contexts = {}
        for node in root.findall(tagname_context, namespaces=namespaces):
            c_id = node.get('id')
            context = TimeContext.fromXmlNode(node)

            if context is not None:
                contexts[c_id] = context
                company.contexts.append(context)

        # get data dependent on contexts
        for fieldname, tagname in fields.items():
            for node in root.findall(tagname, namespaces=namespaces):
                try:
                    context_id = node.get('contextRef')
                    contexts[context_id].fields[fieldname] = node.text

                except KeyError:
                    raise KeyError('Matching <context>-element for contextRef-attribute not found')


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


json_companies = [c.to_dict() for c in all_companies]

@app.route("/all.json")
def all_json():
    # return jsonify(**f)
    return jsonify(companies=json_companies)

@app.route("/company/<int:cvr>.json")
def company_json(cvr):
    print(cvr)
    return jsonify(**company_dictionary[str(cvr)].to_dict())

@app.route("/all.csv")
def all_csv():
    pseudofile = StringIO()
    spamwriter = UnicodeWriter(pseudofile, encoding='utf-8') #, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    header =  ','.join([
        'company.name',
        'company.cvr',
        'context.year',
        'grossprofitloss',
    ])

    for company in all_companies:
        for context in company.contexts:
            if 'grossprofitloss' in context.fields:
                spamwriter.writerow([
                    company.name,
                    company.cvr,
                    context.year,
                    context.fields['grossprofitloss'],
                ])

    return Response(header + '\n' + pseudofile.getvalue(), mimetype='text/csv')





parser = argparse.ArgumentParser(description='A small webserver for hosting the cvr-aarsregnskaber-webservice')
parser.add_argument('--debug', action='store_true', help='Run the server in debug mode')

args = parser.parse_args()

if __name__=="__main__":
    if args.debug:
        app.run(debug=True)
    else:
        app.run(host='0.0.0.0', port=80)
