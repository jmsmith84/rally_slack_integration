#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime, timedelta
from slacker import Slacker
from flask import Flask, request, json
from pyral import Rally

# Configuration Loading
conf_f = open('.rallyhook.json')
conf_s = conf_f.read()
conf = json.loads(str(conf_s), encoding='utf-8')
conf_f.close()

rally_c = { k: v.encode('utf-8') for k, v in conf.get('rally').iteritems() }
slack_c = { k: v.encode('utf-8') for k, v in conf.get('slack').iteritems() }
rallyhook_c = conf.get('rallyhook')

# API Auth
slack = Slacker(slack_c.get('key'))
rally = Rally(
    server = rally_c.get('server'),
    user = rally_c.get('user'),
    password = rally_c.get('password'),
    apikey = rally_c.get('apikey'),
    workspace = rally_c.get('workspace'),
    project = rally_c.get('project')
)
app = Flask(rallyhook_c.get('appname'))

#Routes
@app.route('/notify/vicaarious', methods = ['POST', 'GET'])
def rallybot():
    app.logger.info(request.headers)
    app.logger.info(request.get_json())
    return 'hello', 200

if (__name__ == '__main__'):
    app.run(
        host = rallyhook_c.get('host'),
        port = rallyhook_c.get('port'),
        ssl_context =( rallyhook_c.get('cert'), rallyhook_c.get('key')),
        debug = False
    )

