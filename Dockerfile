FROM amazonlinux:latest

VOLUME /rally_slack_integration
EXPOSE 5050

RUN yum -y update
RUN yum -y upgrade

RUN curl -O https://bootstrap.pypa.io/get-pip.py
RUN python get-pip.py
RUN pip install virtualenv

