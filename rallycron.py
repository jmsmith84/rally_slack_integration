#need to be running python2 (built with 2.7, python DOES NOT WORK )
#pip install pyral (the python-rally connector) as slacker (the slack connector)
import sys
import os.path
from datetime import datetime
from datetime import timedelta
from pyral import Rally
from slacker import Slacker

def parse_config(filename):
    filetext = open(filename)
    data = []
    for line in filetext:
        row = line.strip().split('=')
        if len(row) == 2:
            data.append(row)

    return dict(data)

# Get command line argument for loading config file
if len(sys.argv) < 2:
    print "Argument needed, ie. `rallycron.py team-name`"
    sys.exit()

configFilename = sys.argv[1] + '.config'
if not os.path.isfile(configFilename):
    print configFilename + ': file does not exist.'
    sys.exit()

config = parse_config(configFilename)

slack = Slacker(config.get('slack_api_key', ''))
server = config.get('rally_server', 'rally1.rallydev.com')
workspace = config.get('rally_workspace', '')
project = config.get('rally_project', '')
apikey = config.get('rally_api_key', '')
channel = config.get('slack_channel', '#rally')
botusername = config.get('slack_bot_username', 'rallybot')

#Assume this system runs (via cron) every 15 minutes.
interval = config.get('cron_interval_minutes', 15) * 60

# Artifact item "types" to be allowed to send to Slack
itemFilters = config.get('rally_item_filters', '').split(',')

#format of the date strings as we get them from rally
format = "%Y-%m-%dT%H:%M:%S.%fZ"

print "Rally Slackbot BEGIN"

#create the rally service wrapper (as we are using an API key, we can leave out the username and password)
rally = Rally(server, '', '', apikey=apikey, workspace=workspace, project=project)

#build the query to get only the artifacts (user stories and defects) updated in the last day
querydelta = timedelta(days=-1)
querystartdate = datetime.utcnow() + querydelta;
query = 'LastUpdateDate > ' + querystartdate.isoformat()

response = rally.get('Artifact', fetch=True, query=query, order='LastUpdateDate desc')

for artifact in response:
    print "Artifact found: " + artifact.Name
    include = False

    #start building the message string that may or may not be sent up to slack
    postmessage = '*' + artifact.FormattedID + '*'
    postmessage = postmessage + ': ' + artifact.Name + '\n';
    for revision in artifact.RevisionHistory.Revisions:
        revisionDate = datetime.strptime(revision.CreationDate, format)
        age = revisionDate - datetime.utcnow()
        seconds = abs(age.total_seconds())
        #only even consider this story for inclusion if the timestamp on the revision is less than interval seconds old
        if seconds < interval:
            description = revision.Description
            items = description.split(',')

            for item in items:
                item = item.strip()
                #filter down to only updates we care about
                for filterStr in itemFilters:
                  if item.startswith(filterStr + ' '):

                    #modified to push all updates for now
                    postmessage = postmessage  + "> " + item + ' \n';
                    print postmessage
                    include = True
                    break


    if include:
        print "Attempting to send to Slack"
        postmessage = postmessage + 'https://' + server + '/#/search?keywords=' + artifact.FormattedID + '\n'
        slack.chat.post_message(channel=channel, text=postmessage, username=botusername, as_user=True)

print "Rally Slackbot END"
