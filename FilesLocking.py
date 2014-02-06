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
import subprocess
import math


st_version = 2
if sublime.version() == '' or int(sublime.version()) > 3000:
	st_version = 3


# fix for ST2
cprint = globals()["__builtins__"]["print"]



def plugin_loaded():
	global settings, platform
	settings = sublime.load_settings('FilesLocking.sublime-settings')
	platform = sublime.platform()
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


	def on_modified(self, view):
		if (st_version == 3):
			return
		on_modified_async(view)
		#cprint('MODIFIED');

	def on_modified_async(self, view):
		#cprint('MODIFIED');
		locked = Locker.check_lock(view, False);
		if (not locked):
			Locker.lock_file(view);

	def on_pre_save(self, view):
		if (st_version == 3):
			return
		on_pre_save_async(view)
		#cprint('SAVED');

	def on_pre_save_async(self, view):
		#cprint('SAVED');
		locked = Locker.check_lock(view, True);
		if (not locked):
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

		file_exclude_patterns.append('*.py')

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
		try:
			f = open(lock_file_name, 'w')
			f.write(text)
			f.close()
		except Exception as e:
			cprint(e)

		#hide lock file
		#Locker.hide_file(lock_file_name)

		msg = 'Lock set to file '+filename
		sublime.status_message(msg)
		cprint(msg)

	@staticmethod
	def hide_file(lock_file_name):
		try:
			if (platform == "windows"):
				startupinfo = subprocess.STARTUPINFO()
				startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
				startupinfo.wShowWindow = subprocess.SW_HIDE
				subprocess.call(['attrib', '+H', lock_file_name], startupinfo=startupinfo, shell=False)
			else:
				subprocess.call(['chflags', 'hidden', lock_file_name])
		except Exception as e:
			cprint(e)


	@staticmethod
	def unlock_file(view):
		cprint('FORCE CLOSE: '+str(Locker.force_close))
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
			cprint(msg)

	@staticmethod
	def check_lock(view, from_save = False):
		filename = view.file_name()
		if (not filename):
			return

		new_name = filename+'.'+Locker.lock_ext
		locked = False
		if (os.path.isfile(new_name)):
			locktime = os.path.getmtime(new_name)
			lock_user = settings.get('fileslocking_user', 'Guest');
			lock_hostname = socket.gethostname()
			lock_ip = socket.gethostbyname(lock_hostname)
			try:
				with open(new_name, 'rU') as f:
					lockinfo = f.read().splitlines()
					locker = lockinfo[0]
					hostname = lockinfo[1]
					if locker == lock_user and hostname == lock_hostname:
						#print("You opened a file that was locked by yourself.")
						Locker.force_close = True
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

						readablemsg = (str(math.ceil(minago)) + minstr) + " ago"
						error_msg = locker + " locked " + filename + " at " + time.strftime("%H:%M", time.localtime(locktime)) + " (about a " + readablemsg + ")."
						Locker.force_close = True
						sublime.error_message(error_msg)
						#view.window().run_command("close")
						locked = True
			except Exception as e:
						cprint(e)
		return locked

