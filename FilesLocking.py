#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sublime
import sublime_plugin
import sys
import os
import shutil
import re
import string
import platform
import socket
import time

st_version = 2
if sublime.version() == '' or int(sublime.version()) > 3000:
	st_version = 3


# fix for ST2
cprint = globals()["__builtins__"]["print"]



def plugin_loaded():
	global settings
	settings = sublime.load_settings('FilesLocking.sublime-settings')
	cprint('FilesLocking: Plugin Initialized')
	windows = sublime.windows()
	for window in windows:
		views = window.views()
		for view in views:
			Locker.lock_file(view)


if st_version == 2:
	plugin_loaded()



class FilesLockingEventListener(sublime_plugin.EventListener):

	def on_close(self, view):
		#cprint('CLOSE');
		Locker.unlock_file(view)

	def on_load(self, view):
		if (st_version == 3):
			return
		#cprint('OPEN');

	def on_load_async(self, view):
		#cprint('OPEN');
		Locker.check_lock(view);

		Locker.lock_file(view);


	def console(self, text):
		cprint(text)

	def encode(self, text):
		if (st_version == 2):
			if isinstance(text, unicode):
				text = text.encode('UTF-8')
		elif (st_version == 3):
			if isinstance(text, str):
				text = text.encode('UTF-8')
		return text


class Locker(object):
	lock_ext = 'sublime-lock';
	force_close = False;

	@staticmethod
	def lock_file(view):
		gsettings = sublime.load_settings('Preferences.sublime-settings')
		file_exclude_patterns = gsettings.get('file_exclude_patterns', '');
		file_exclude_patterns.append('*.'+Locker.lock_ext)

		filename = view.file_name()
		if (not filename):
			return
		path = os.path.expanduser(os.path.split(filename)[0])
		name = os.path.expanduser(os.path.split(filename)[1])
		fname, fextension = os.path.splitext(name)

		if (fextension == ''):
			fextension = fname

		if ('*'+fextension in file_exclude_patterns):
			return False

		lock_file_name = filename+'.'+Locker.lock_ext

		lock_user = settings.get('fileslocking_user', 'Guest');
		lock_hostname = socket.gethostname()
		lock_ip = socket.gethostbyname(lock_hostname)

		text = []
		text.append(lock_user)
		text.append(lock_hostname)
		text.append(lock_ip)
		text = "\n".join(text)
		f = open(lock_file_name, 'w')
		f.write(text)
		f.close()

		msg = 'Lock set to file '+filename
		sublime.status_message(msg)


	@staticmethod
	def unlock_file(view):
		if (Locker.force_close):
			Locker.force_close = False
			return

		filename = view.file_name()
		if (not filename):
			return
		new_name = filename+'.'+Locker.lock_ext
		if (os.path.isfile(new_name)):
			os.remove(new_name)
			msg = 'Lock removed to file '+filename
			sublime.status_message(msg)

	@staticmethod
	def check_lock(view):
		filename = view.file_name()
		new_name = filename+'.'+Locker.lock_ext
		locked = False
		if (os.path.isfile(new_name)):
			locktime = os.path.getmtime(new_name)
			lock_user = settings.get('fileslocking_user', 'Guest');
			try:
				with open(new_name, 'rU') as f:
					lockinfo = f.read().splitlines()
					locker = lockinfo[0]
					if locker == lock_user:
						print("You opened a file that was locked by yourself.")
					else:
						# File is already locked, so don't let user open it.
						f.close()
						lockdiff = int(time.time()) - locktime
						if (lockdiff <= 60):
							lockdiff = 60

						if (lockdiff >= 3600):
							minago = lockdiff // 3600
							minstr = ' hours'
						else:
							minago = lockdiff // 60
							minstr = ' minutes'

						readablemsg = (str(minago) + minstr) + " ago"

						error_msg = locker + " locked " + filename + " at " + time.strftime("%H:%M", time.localtime(locktime)) + " (about " + readablemsg + ")."
						sublime.error_message(error_msg)
						Locker.force_close = True
						view.window().run_command("close")
			except Exception as e:
						cprint(e)


