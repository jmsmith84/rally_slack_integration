#!/usr/bin/env python2
#Dependencies: pip2 install pyral (the Rally connector) and slacker (the Slack connector)
import sys
import os.path
from datetime import datetime
from datetime import timedelta
from pyral import Rally
from pyral.context import RallyRESTAPIError
from slacker import Slacker

APP_DISPLAY_NAME = "RallyCronBot"
CONFIG_PATH = "./config"
REVISION_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
verbose = False
startTime = datetime.utcnow()
includeCount = 0

def send_911_message_if_time(error, channel, timeRange):
    timeRange = timeRange.split('-')
    if len(timeRange) < 2:
        print "Invalid emergency time range value [{}]".format(timeRange)
        return

    now = datetime.now()
    ymdString = '%Y%m%d'
    for i in range(0, 2):
        timeRange[i] = datetime.strptime(now.strftime(ymdString) + timeRange[i], ymdString + '%H:%M')
        debug_info("911 timerange {}: {}".format(i, timeRange[i]))

    if now >= timeRange[0] and now <= timeRange[1]:
        debug_info("Sending 911 message")
        send_slack_message(channel, "I'm unable to get data from Rally, and here's why: ```{}```".format(error))

def create_rally_conn(apikey, workspace, project, emergencyChannel, emergencyTimeRange):
    debug_info("Creating Rally connection wrapper [{}]".format(server))
    rally = False
    try:
        rally = Rally(server, '', '', apikey=apikey, workspace=workspace, project=project)
    except RallyRESTAPIError as err:
        print("Pyral REST API Error: {}".format(err))
        send_911_message_if_time(err, emergencyChannel, emergencyTimeRange)
    except:
        print("Error: {}", sys.exc_info()[0])
    return rally

def debug_info(string):
    if verbose:
        print string

def print_cmd_help():
    print "{} usage: {} [-v] config-name".format(APP_DISPLAY_NAME, __file__)
    print "  config-name: Name that has matching config file (ie. {}/config-name.cfg)".format(CONFIG_PATH)
    print "  -v: Verbose mode (enable debug info)"

def parse_config(filepath):
    debug_info("Loading config file: " + filepath)

    filetext = open(filepath)
    data = []
    for line in filetext:
        row = line.strip().split('=')
        if len(row) == 2:
            data.append(row)

    return dict(data)

def send_slack_message(channel, message):
    slack.chat.post_message(channel=channel, text=message, username=botUsername, as_user=True)

def build_revision_items_message(items):
    global includeCount

    output = ''
    for item in items:
        item = item.strip()
        #filter down to only updates we care about
        include = False
        for filterStr in itemFilters:
            if item.startswith(filterStr + ' '):
                #modified to push all updates for now
                output = output + "> " + item + ' \n';
                include = True
                break

        if include:
            includeCount += 1
            debug_info("INCLUDE: " + item)
        else:
            debug_info("IGNORE: " + item)

    return output

if len(sys.argv) < 2:
    print_cmd_help()
    sys.exit()

configNameArg = sys.argv[1]
if sys.argv[1] == '-v':
    verbose = True
    if len(sys.argv) < 3:
        print_cmd_help()
        sys.exit()
    configNameArg = sys.argv[2]

configPath = os.path.dirname(os.path.realpath(__file__)) + '/' + CONFIG_PATH
configFullPath = configPath + '/' + configNameArg + '.cfg'

if not os.path.isfile(configFullPath):
    print 'ERROR - File Not Found: ' + configFullPath
    sys.exit()

config = parse_config(configFullPath)
server = config.get('rally_server', 'rally1.rallydev.com')
workspace = config.get('rally_workspace', '')
project = config.get('rally_project', '')
apikey = config.get('rally_api_key', '')
channel = config.get('slack_channel', '#rally')
botUsername = config.get('slack_bot_username', 'rallybot')
#Set interval to exactly the same as the cronjob itself
interval = config.get('cron_interval_minutes', 15) * 60
#Artifact item "types" to be allowed to send to Slack
itemFilters = config.get('rally_item_filters', '').split(',')

debug_info("{} - BEGIN - {}".format(APP_DISPLAY_NAME, startTime))

debug_info("Creating Slack connection wrapper")
slack = Slacker(config.get('slack_api_key', ''))

rally = create_rally_conn(apikey, workspace, project, config.get('slack_911_channel', channel), config.get('slack_911_timerange', '00:00-00:30'))
if not rally:
    print "Rally connection failed"
    sys.exit()

#Build the query to get only the artifacts (user stories, defects, etc.) updated in the last day
queryDelta = timedelta(days=-1)
queryStartDate = startTime + queryDelta;
query = 'LastUpdateDate > ' + queryStartDate.isoformat()

debug_info("Fetching from Rally: " + query)
response = rally.get('Artifact', fetch=True, query=query, order='LastUpdateDate desc')

for artifact in response:
    debug_info("Artifact found: " + artifact.Name)
    includeCount = 0

    #Start building the message string that may or may not be sent up to slack
    postMessage = '*' + artifact.FormattedID + '*'
    postMessage = postMessage + ': ' + artifact.Name + '\n';
    for revision in artifact.RevisionHistory.Revisions:
        revisionDate = datetime.strptime(revision.CreationDate, REVISION_DATE_FORMAT)
        age = revisionDate - startTime
        seconds = abs(age.total_seconds())
        #Only even consider this story for inclusion if the timestamp on the revision is less than interval seconds old
        if seconds < interval:
            postMessage = postMessage + build_revision_items_message(revision.Description.split(','))

    if includeCount > 0:
        debug_info("Attempting to send to Slack with {} items".format(includeCount))
        postMessage = postMessage + 'https://{}/#/search?keywords={}\n'.format(server, artifact.FormattedID)
        send_slack_message(channel, postMessage)
    else:
        debug_info("No items to send")

debug_info("{} - END - {}".format(APP_DISPLAY_NAME, datetime.utcnow()))
