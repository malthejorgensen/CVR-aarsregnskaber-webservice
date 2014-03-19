from flask import Flask, render_template, request, jsonify

import glob
import datetime
import xml.etree.ElementTree as ET

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

    def __init__(self, cvr):
        self.cvr = cvr


class TimeContext():
    #def __init__(self, year, start_date, end_date):

    @classmethod
    def fromXmlNode(cls, node):
        node_period = node.find('period')
        if node_period is None:
            return None

        self = cls()
        if node_period.find('instant') is not None:
            self.instant_date = datetime.strptime(str_date, '%Y-%m-%d')
        elif node_period.find('startDate') is not None and \
             node_period.find('endDate') is not None:
            self.start_date = datetime.strptime(node_period.find('startDate').text, '%Y-%m-%d')
            self.end_date = datetime.strptime(node_period.find('endDate').tex, '%Y-%m-%d')
            self.year = self.start_date.year


for filename in glob.glob('aarsregnskaber/*.xml'):
    with open(filename, 'r') as f:
        dom = ET.parse(f)
        root = dom.getroot()

        # Get CVR
        cvr = root.find(tagname_cvr, namespaces=namespaces).text
        companyname = root.find(tagname_companyname, namespaces=namespaces).text

        all_companies.append(companyname)

        # build contexts
        contexts = {}
        for node in root.findall(tagname_context, namespaces=namespaces):
            c_id = node.get('id')
            contexts[c_id] = TimeContext.fromXmlNode(node)

        # get data dependent on contexts
        for node in root.findall(tagname_grossprofitloss, namespaces=namespaces):
            try:
                context_id = node.get('contextRef')
                contexts[context_id]
            except KeyError:
                raise 'Matching <context>-element for contextRef-attribute not found'

        # if node is None:
        #     print(filename)


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/all.json")
def all_json():
    # return jsonify(**f)
    return jsonify(companies=all_companies)


if __name__=="__main__":
    # app.run(host='0.0.0.0',port=80, debug=True)
    #app.run()
    app.run(debug=True)
