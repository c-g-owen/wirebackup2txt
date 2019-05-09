#! /usr/env python

import datetime
import getpass
import httplib
import json
import optparse
import os
import shutil
import sys
import tempfile
import zipfile
from operator import attrgetter

user_agent = 'bkup2txt'
host = 'prod-nginz-https.wire.com'

def get_bkup_info(bkup_file):
	zf = zipfile.ZipFile(bkup_file)
	tmpdir = tempfile.mkdtemp()
	zf.extractall(tmpdir)
	convs = json.load(open(os.path.join(tmpdir, 'conversations.json')))
	events = json.load(open(os.path.join(tmpdir, 'events.json')))
	shutil.rmtree(tmpdir)

	return (convs, events)


def do_login(host, username=None, password=None):
	if username is None:
		username = raw_input('Email: ')
	if password is None:
		password = getpass.getpass('Password: ')
	conn = httplib.HTTPSConnection(host)
	conn.request('POST', '/login', json.dumps({'email': username,
		'password': password}),
		{'Content-Type': 'application/json',
		'User-Agent': user_agent})
	response = conn.getresponse()
	if response.status != 200:
		print 'Login failed.'
		sys.exit(1)

	info = json.loads(response.read())
	token = info['access_token']
	userid = info['user']
	conn.close()
	return (userid, token)


def get_user_name(userid, host, token):
	username = None
	conn = httplib.HTTPSConnection(host)
	conn.request('GET', '/users/%s' % userid, None,
		{ 'Authorization': 'Bearer %s' % token,
		'User-Agent': user_agent })
	response = conn.getresponse()
	if response.status == 200:
		r = response.read()
		username = json.loads(r)['name']
	conn.close()

	return username
	

def get_user_names(convs, host, token):
	users = {}

	for c in convs:
		for o in c['others']:
			if o not in users:
				username = get_user_name(o, host, token)
				if username:
					users[o] = username
	return users


def export_conv(convid, events, users, dstfile):
	f = open(dstfile, 'w')

	conv_events = [x for x in events if x['conversation'] == convid
		and x['type'] == 'conversation.message-add']

	conv_events.sort(key = lambda e: e['time'])

	last_date = None
	last_time = datetime.datetime(datetime.MINYEAR, 1, 1, 0, 0, 0)
	last_user = None
	for e in conv_events:
		msg_time = datetime.datetime.strptime(e['time'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
		if msg_time.date() != last_date:
			f.write(u'\n{}\n'.format(msg_time.date()))
			last_date = msg_time.date()

		username = 'Unknown'
		if e['from'] in users:
			username = users[e['from']]

		tdiff = msg_time - last_time
		if (tdiff > datetime.timedelta(seconds = 120)) or \
			last_user != e['from']:
			f.write(u'\n{} '.format(msg_time.strftime('%H:%M')))
			f.write(username.encode('utf-8'))
			f.write(u'\n')
			last_time = msg_time
			last_user = e['from']
		else:
			f.write(u'\n')

		f.write(e['data']['content'].encode('utf-8'))
		f.write(u'\n')


if __name__ == '__main__':

	srcfile = None

	usage = 'usage: %prog [options] <backup file>'
	parser = optparse.OptionParser(usage=usage)
	parser.add_option('-e', '--email', dest='username',
		help='Email address for logging in')
	parser.add_option('-p', '--password', dest='password',
		help='Password for logging in')
	parser.add_option('-d', '--dest-path', dest='dstpath', default='extract',
		help='Destination directory to store the extracted files (default=extract)')

	(options, args) = parser.parse_args()

	username = options.username
	password = options.password
	dstpath = options.dstpath

	if len(args) != 1:
		parser.print_usage()
		exit()

	srcfile = args[0]
	(convs, events) = get_bkup_info(srcfile)

	if os.path.exists('users.json'):
		users = json.load(open('users.json'))
	else:
		(userid, token) = do_login(host, username, password)
		users = get_user_names(convs, host, token)
		users[userid] = get_user_name(userid, host, token)
		json.dump(users, open('users.json', 'w'))

	if not os.path.exists(dstpath):
		os.makedirs(dstpath)

	for c in convs:
		if 'name' in c and c['name']:
			conv_name = c['name']
		else:
			conv_name = ''
			for o in c['others']:
				if o in users:
					conv_name += users[o] + '_'
				else:
					conv_name += o + '_'
			conv_name = conv_name[:-1]

		if not conv_name:
			conv_name = 'Unnamed Conversation'

		conv_name = conv_name.replace('/', '-').replace('\\', '-').encode('ascii', 'replace')

		dstfile = os.path.join(dstpath, '{}.txt'.format(conv_name))
		idx = 1
		while os.path.exists(dstfile):
			dstfile = os.path.join(dstpath, '{}_{}.txt'.format(conv_name, idx))
			idx += 1

		print('Exporting conv {}'.format(conv_name))
		export_conv(c['id'], events, users, dstfile)




