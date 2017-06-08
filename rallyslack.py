#note, you'll need to be running python2 (built with 2.7, python DOES NOT WORK )
#you'll need to pip install pyral (the python-rally connector) as slacker (the slack connector)

from datetime import datetime
from datetime import timedelta
from pyral import Rally
from slacker import Slacker

print "Rally Slackbot INIT"

slack = Slacker('your slack key')
server = "rally1.rallydev.com"

#as we are using an API key, we can leave out the username and password
user = ""
password = ""

workspace = "Your Workspace"
project = "Your Project"
apikey = "Your API Key"

#which slack channel does this post to?
channel = "#your_channel"

#user that has access to the slack channel and will be posting the messages
botusername = "rallybot"

#Assume this system runs (via cron) every 15 minutes.
interval = 15 * 60

#format of the date strings as we get them from rally
format = "%Y-%m-%dT%H:%M:%S.%fZ"

#create the rally service wrapper
rally = Rally(server, user, password, apikey=apikey, workspace=workspace, project=project)


#build the query to get only the artifacts (user stories and defects) updated in the last day
querydelta = timedelta(days=-1)
querystartdate = datetime.utcnow() + querydelta;
query = 'LastUpdateDate > ' + querystartdate.isoformat()

response = rally.get('Artifact', fetch=True, query=query, order='LastUpdateDate desc')

for artifact in response:
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
                #the only kinds of updates we care about are..
                itemFilters = ['FLOW STATE changed ','STATE changed ','TASKS added ','OWNER ','DESCRIPTION ','NOTES ']

                for filterStr in itemFilters:
                  if item.startswith(filterStr):

                    #Modified to push all updates for now
                    postmessage = postmessage  + "> " + item + ' \n';
                    print postmessage
                    include = True

    if include:
        print "Attempting to send to Slack"
        postmessage = postmessage + 'https://' + server + '/#/search?keywords=' + artifact.FormattedID + '\n'
        slack.chat.post_message(channel=channel, text=postmessage, username=botusername, as_user=True)

print "Rally Slackbot END"



