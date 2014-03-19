from __future__ import print_function

from flask import Flask, render_template, request, jsonify, Response

import glob
from cStringIO import StringIO

from datetime import datetime
import xml.etree.ElementTree as ET

import csv
from unicode_csv import UnicodeWriter

namespaces = {
    'c': 'http://xbrl.dcca.dk/gsd',
    'd': 'http://xbrl.dcca.dk/fsa'
    #http://www.xbrl.org/2003/instance
}
# tagname_cvr = # '{http://xbrl.dcca.dk/gsd}IdentificationNumberCvrOfSubmittingEnterprise' # Not all files contains this
tagname_cvr = '{http://xbrl.dcca.dk/gsd}IdentificationNumberCvrOfReportingEntity'
tagname_companyname = '{http://xbrl.dcca.dk/gsd}NameOfReportingEntity'
tagname_grossprofitloss = '{http://xbrl.dcca.dk/fsa}GrossProfitLoss'

tagname_context = '{http://www.xbrl.org/2003/instance}context'


all_companies = []

class Company():

    def __init__(self, cvr, name):
        self.cvr = cvr
        self.name = name
        self.contexts = []

    def to_dict(self):
        contexts = {}
        for c in self.contexts:
            if c.data:
                contexts[c.year] = c.to_dict()

        return {
           'cvr': self.cvr,
           'name': self.name,
           'regnskaber': contexts
        }


class TimeContext():
    def __init__(self):
        self.start_date = None
        self.end_date = None
        self.instant_date = None
        self.year = None
        self.data = {}
        self.context_id = {}

    @classmethod
    def fromXmlNode(cls, node):
        node_period = node.find('{http://www.xbrl.org/2003/instance}period')
        if node_period is None:
            return None

        self = cls()
        self.data = {}
        self.context_id = node.get('id')

        if node_period.find('{http://www.xbrl.org/2003/instance}instant') is not None:
            self.instant_date = datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}instant').text, '%Y-%m-%d')
            self.year = self.instant_date.year
            return None
        elif node_period.find('{http://www.xbrl.org/2003/instance}startDate') is not None and \
             node_period.find('{http://www.xbrl.org/2003/instance}endDate') is not None:
            self.start_date = datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}startDate').text, '%Y-%m-%d')
            self.end_date = datetime.strptime(node_period.find('{http://www.xbrl.org/2003/instance}endDate').text, '%Y-%m-%d')
            self.year = self.start_date.year
        return self

    def to_dict(self):
        d = {
           'start_date': self.start_date,
           'end_date': self.end_date,
           'year': self.year,
           'context_id': self.context_id,
        }
        d.update(self.data)
        return d


for filename in glob.glob('aarsregnskaber/*.xml'):
    with open(filename, 'r') as f:
        dom = ET.parse(f)
        root = dom.getroot()

        # Get CVR
        cvr = root.find(tagname_cvr, namespaces=namespaces).text
        companyname = root.find(tagname_companyname, namespaces=namespaces).text

        company = Company(
          cvr=cvr,
          name=companyname,
        )
        all_companies.append(company)

        # build contexts
        contexts = {}
        for node in root.findall(tagname_context, namespaces=namespaces):
            c_id = node.get('id')
            context = TimeContext.fromXmlNode(node)

            if context is not None:
                contexts[c_id] = context
                company.contexts.append(context)

        # get data dependent on contexts
        for node in root.findall(tagname_grossprofitloss, namespaces=namespaces):
            try:
                context_id = node.get('contextRef')
                contexts[context_id].data['grossprofitloss'] = node.text

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
            if 'grossprofitloss' in context.data:
                spamwriter.writerow([
                    company.name,
                    company.cvr,
                    context.year,
                    context.data['grossprofitloss'],
                ])

    return Response(header + '\n' + pseudofile.getvalue(), mimetype='text/csv')


if __name__=="__main__":
    # app.run(host='0.0.0.0',port=80, debug=True)
    #app.run()
    app.run(debug=True)
